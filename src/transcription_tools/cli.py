"""Command-line entry point for the transcription-tools package.

Subcommand-based so future tools (e.g. an audio/video transcription
subcommand) can be added alongside `srt-to-text` without breaking existing
usage.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import srt_to_text, transcribe


def _resolve_destination(
    source_file: Path,
    fmt: str,
    output_arg: Path | None,
    input_root: Path,
    single_file_input: bool,
) -> Path:
    if output_arg is None:
        return source_file.with_suffix(f".{fmt}")
    if single_file_input and not output_arg.is_dir():
        return output_arg
    # Mirror the input tree under the output directory so that same-named files
    # in different subdirectories do not overwrite each other when --recursive.
    relative = source_file.relative_to(input_root)
    return output_arg / relative.with_suffix(f".{fmt}")


def _output_is_not_a_directory(output_arg: Path | None, single_file_input: bool) -> bool:
    return (
        output_arg is not None
        and not single_file_input
        and output_arg.exists()
        and not output_arg.is_dir()
    )


def _run_srt_to_text(args: argparse.Namespace) -> int:
    input_path: Path = args.input

    try:
        srt_files = srt_to_text.find_srt_files(input_path, recursive=args.recursive)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not srt_files:
        print(f"error: no .srt files found in {input_path}", file=sys.stderr)
        return 1

    output_arg = Path(args.output) if args.output else None
    single_file_input = input_path.is_file()
    input_root = input_path.parent if single_file_input else input_path

    if _output_is_not_a_directory(output_arg, single_file_input):
        print(
            f"error: --output must be a directory when input is a directory: "
            f"{output_arg}",
            file=sys.stderr,
        )
        return 1

    failures = 0
    for srt_file in srt_files:
        destination = _resolve_destination(
            srt_file, args.format, output_arg, input_root, single_file_input
        )
        try:
            transcript = srt_to_text.convert_srt(srt_file, fmt=args.format)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(transcript, encoding="utf-8")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            print(f"error: {srt_file}: {exc}", file=sys.stderr)
            failures += 1
            continue
        print(f"Wrote {destination}")

    return 1 if failures else 0


def _run_transcribe(args: argparse.Namespace) -> int:
    input_path: Path = args.input

    try:
        media_files = transcribe.find_media_files(input_path, recursive=args.recursive)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not media_files:
        print(
            f"error: no audio or video files found in {input_path}",
            file=sys.stderr,
        )
        return 1

    output_arg = Path(args.output) if args.output else None
    single_file_input = input_path.is_file()
    input_root = input_path.parent if single_file_input else input_path

    if _output_is_not_a_directory(output_arg, single_file_input):
        print(
            f"error: --output must be a directory when input is a directory: "
            f"{output_arg}",
            file=sys.stderr,
        )
        return 1

    pending = []
    for media_file in media_files:
        destination = _resolve_destination(
            media_file, args.format, output_arg, input_root, single_file_input
        )
        # Transcribing a course library takes hours and gets interrupted, so a
        # re-run resumes by default instead of redoing finished files.
        if destination.exists() and not args.overwrite:
            print(f"Skipping {media_file} (output exists: {destination})")
            continue
        pending.append((media_file, destination))

    if not pending:
        print("Nothing to transcribe; all outputs exist (use --overwrite to redo).")
        return 0

    # Loading the model is the slow part, so do it once for the whole batch —
    # and before any transcription, so a bad model name fails fast.
    try:
        model = transcribe.load_model(
            model=args.model,
            device=args.device,
            compute_type=args.compute_type,
            model_dir=args.model_dir,
        )
    except transcribe.MissingBackendError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"error: could not load model {args.model!r}: {exc}", file=sys.stderr)
        return 1

    failures = 0
    total = len(pending)
    for position, (media_file, destination) in enumerate(pending, start=1):
        print(f"[{position}/{total}] Transcribing {media_file} ...")
        started = time.monotonic()
        try:
            segments, language = transcribe.transcribe_media(
                model,
                media_file,
                language=args.language,
                vad_filter=not args.no_vad,
            )
            transcript = transcribe.format_transcript(
                segments, fmt=args.format, title=media_file.stem
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(transcript, encoding="utf-8")
        # PyAV raises av.error.* for undecodable media, which subclass
        # ValueError/OSError; CTranslate2 raises RuntimeError. Between them
        # that covers "this one file is broken" without swallowing everything.
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"error: {media_file}: {exc}", file=sys.stderr)
            failures += 1
            continue
        elapsed = time.monotonic() - started
        print(
            f"Wrote {destination} "
            f"({language}, {len(segments)} segments, {elapsed:.1f}s)"
        )

    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transcription-tools",
        description=(
            "CLI tools for turning course subtitles and recordings into transcripts."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    srt_parser = subparsers.add_parser(
        "srt-to-text",
        help="Convert .srt subtitle files into plain-text or Markdown transcripts.",
    )
    srt_parser.add_argument(
        "input",
        type=Path,
        help="Path to a .srt file, or a directory containing .srt files.",
    )
    srt_parser.add_argument(
        "--format",
        choices=srt_to_text.SUPPORTED_FORMATS,
        default="txt",
        help="Output format (default: txt).",
    )
    srt_parser.add_argument(
        "--output",
        "-o",
        help=(
            "Output file path when input is a single file, or output directory "
            "when input is a directory. Defaults to next to the source file(s)."
        ),
    )
    srt_parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recurse into subdirectories when input is a directory.",
    )
    srt_parser.set_defaults(handler=_run_srt_to_text)

    transcribe_parser = subparsers.add_parser(
        "transcribe",
        help="Transcribe audio or video files into subtitles or transcripts.",
        description=(
            "Transcribe audio or video files with Whisper. Requires the "
            f"optional backend: {transcribe.INSTALL_HINT}"
        ),
    )
    transcribe_parser.add_argument(
        "input",
        type=Path,
        help="Path to an audio/video file, or a directory containing them.",
    )
    transcribe_parser.add_argument(
        "--format",
        choices=transcribe.SUPPORTED_FORMATS,
        default="srt",
        help=(
            "Output format (default: srt, which media players pick up as a "
            "subtitle track and srt-to-text can convert further)."
        ),
    )
    transcribe_parser.add_argument(
        "--output",
        "-o",
        help=(
            "Output file path when input is a single file, or output directory "
            "when input is a directory. Defaults to next to the source file(s)."
        ),
    )
    transcribe_parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Recurse into subdirectories when input is a directory.",
    )
    transcribe_parser.add_argument(
        "--model",
        default=transcribe.DEFAULT_MODEL,
        help=(
            "Whisper model size, e.g. tiny, base, small, medium, large-v3, "
            f"turbo (default: {transcribe.DEFAULT_MODEL}). Downloaded on first "
            "use."
        ),
    )
    transcribe_parser.add_argument(
        "--language",
        help="Spoken language code, e.g. en. Detected automatically if omitted.",
    )
    transcribe_parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
        help="Compute device (default: auto, which uses CUDA when available).",
    )
    transcribe_parser.add_argument(
        "--compute-type",
        help=(
            "CTranslate2 compute type, e.g. int8, float16, float32. Defaults to "
            "int8 on CPU and float16 on CUDA."
        ),
    )
    transcribe_parser.add_argument(
        "--model-dir",
        type=Path,
        help="Directory to download models into (default: the Hugging Face cache).",
    )
    transcribe_parser.add_argument(
        "--no-vad",
        action="store_true",
        help="Disable the voice-activity filter that skips silent stretches.",
    )
    transcribe_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-transcribe files whose output already exists (skipped by default).",
    )
    transcribe_parser.set_defaults(handler=_run_transcribe)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
