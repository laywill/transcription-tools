"""Transcribe audio and video files to text with Whisper.

The Whisper backend (faster-whisper) is an optional extra and is imported
lazily inside `load_model`, so `srt-to-text` keeps working — and the test
suite keeps running — without it installed.
"""

from __future__ import annotations

import io
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pysrt

from .file_discovery import find_files

SUPPORTED_FORMATS = ("srt", "txt", "md")

AUDIO_EXTENSIONS = (
    ".aac",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
)
VIDEO_EXTENSIONS = (
    ".avi",
    ".flv",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ts",
    ".webm",
    ".wmv",
)
MEDIA_EXTENSIONS = tuple(sorted(AUDIO_EXTENSIONS + VIDEO_EXTENSIONS))

# large-v3-turbo: near large-v3 accuracy at a fraction of the decode cost,
# which is what makes transcribing a whole course library practical.
DEFAULT_MODEL = "turbo"

INSTALL_HINT = 'pip install -e ".[transcribe]"'


class MissingBackendError(RuntimeError):
    """Raised when the optional faster-whisper dependency is not installed."""


@dataclass(frozen=True)
class Segment:
    """One timed chunk of speech, decoupled from the backend's own type."""

    start: float
    end: float
    text: str


def find_media_files(path: Path, recursive: bool = False) -> list[Path]:
    """Resolve a file or directory input into a sorted list of media files."""
    return find_files(
        path, MEDIA_EXTENSIONS, recursive=recursive, label="audio or video"
    )


def resolve_runtime(
    device: str, compute_type: str | None, cuda_available: bool
) -> tuple[str, str]:
    """Pick the device and compute type to hand to CTranslate2."""
    resolved_device = device
    if device == "auto":
        resolved_device = "cuda" if cuda_available else "cpu"

    if compute_type is None:
        # CTranslate2 otherwise keeps the model's float32 weights, which is
        # several times slower on CPU for no accuracy gain worth the wait on a
        # course-length batch.
        compute_type = "float16" if resolved_device == "cuda" else "int8"

    return resolved_device, compute_type


def load_model(
    model: str = DEFAULT_MODEL,
    device: str = "auto",
    compute_type: str | None = None,
    model_dir: Path | None = None,
):
    """Load a Whisper model, downloading it on first use.

    Raises `MissingBackendError` rather than `ImportError` so the CLI can turn
    a missing optional extra into a single actionable message.
    """
    # Imported here, not at module scope, so the backend stays an optional
    # extra: importing this module must not require it.
    # pylint: disable=import-outside-toplevel
    try:
        import ctranslate2  # pyright: ignore[reportMissingImports]
        from faster_whisper import (  # pyright: ignore[reportMissingImports]
            WhisperModel,
        )
    except ImportError as exc:
        raise MissingBackendError(
            f"faster-whisper is not installed. Install the optional extra with: "
            f"{INSTALL_HINT}"
        ) from exc

    resolved_device, resolved_compute_type = resolve_runtime(
        device, compute_type, ctranslate2.get_cuda_device_count() > 0
    )

    return WhisperModel(
        model,
        device=resolved_device,
        compute_type=resolved_compute_type,
        download_root=str(model_dir) if model_dir else None,
    )


def transcribe_media(
    model,
    media_path: Path,
    language: str | None = None,
    vad_filter: bool = True,
) -> tuple[list[Segment], str]:
    """Transcribe one media file, returning its segments and spoken language."""
    segments, info = model.transcribe(
        str(media_path), language=language, vad_filter=vad_filter
    )

    # faster-whisper decodes lazily, so decode errors surface on iteration here
    # rather than on the call above.
    collected = [
        Segment(start=float(seg.start), end=float(seg.end), text=seg.text.strip())
        for seg in segments
    ]

    if not collected:
        raise ValueError(f"No speech detected in {media_path}")

    return collected, getattr(info, "language", None) or "unknown"


def format_transcript(
    segments: Sequence[Segment], fmt: str = "srt", title: str = ""
) -> str:
    """Render segments as SubRip, plain text, or Markdown."""
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format {fmt!r}; expected one of {SUPPORTED_FORMATS}"
        )

    if fmt == "srt":
        return _to_srt(segments)

    transcript = " ".join(text for text in (s.text.strip() for s in segments) if text)

    if fmt == "md":
        return f"# {title}\n\n{transcript}\n"
    return f"{transcript}\n"


def _to_srt(segments: Iterable[Segment]) -> str:
    # Built with pysrt (already a dependency) so timestamp formatting and the
    # block layout match what `srt-to-text` can read back in.
    subs = pysrt.SubRipFile(
        [
            pysrt.SubRipItem(
                index=index,
                start=pysrt.SubRipTime.from_ordinal(round(segment.start * 1000)),
                end=pysrt.SubRipTime.from_ordinal(round(segment.end * 1000)),
                text=segment.text.strip(),
            )
            for index, segment in enumerate(segments, start=1)
        ],
        eol="\n",
    )
    buffer = io.StringIO()
    subs.write_into(buffer)
    return buffer.getvalue()
