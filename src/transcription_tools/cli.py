"""Command-line entry point for the transcription-tools package.

Subcommand-based so future tools (e.g. an audio/video transcription
subcommand) can be added alongside `srt-to-text` without breaking existing
usage.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import srt_to_text


def _resolve_destination(
    srt_file: Path,
    fmt: str,
    output_arg: Path | None,
    single_file_input: bool,
) -> Path:
    if output_arg is None:
        return srt_file.with_suffix(f".{fmt}")
    if single_file_input:
        return output_arg
    return output_arg / srt_file.with_suffix(f".{fmt}").name


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

    for srt_file in srt_files:
        transcript = srt_to_text.convert_srt(srt_file, fmt=args.format)
        destination = _resolve_destination(srt_file, args.format, output_arg, single_file_input)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(transcript, encoding="utf-8")
        print(f"Wrote {destination}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transcription-tools",
        description="CLI tools for turning course subtitles and recordings into transcripts.",
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
