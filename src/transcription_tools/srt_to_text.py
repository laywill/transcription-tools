"""Convert .srt subtitle files into plain-text or Markdown transcripts."""

from __future__ import annotations

from pathlib import Path

import pysrt

from .file_discovery import find_files

SUPPORTED_FORMATS = ("txt", "md")
SRT_EXTENSIONS = (".srt",)


def find_srt_files(path: Path, recursive: bool = False) -> list[Path]:
    """Resolve a file or directory input into a sorted list of .srt files."""
    return find_files(path, SRT_EXTENSIONS, recursive=recursive, label=".srt")


def convert_srt(srt_path: Path, fmt: str = "txt") -> str:
    """Read an .srt file and return it as a plain-text or Markdown transcript."""
    if fmt not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported format {fmt!r}; expected one of {SUPPORTED_FORMATS}"
        )

    try:
        subs = pysrt.open(str(srt_path), error_handling=pysrt.ERROR_RAISE)
    except pysrt.Error as exc:
        raise ValueError(f"Not a valid .srt file: {srt_path} ({exc})") from exc

    if not subs:
        raise ValueError(f"No subtitles found in {srt_path}")

    lines = (sub.text_without_tags.replace("\n", " ").strip() for sub in subs)
    transcript = " ".join(line for line in lines if line)

    if fmt == "md":
        return f"# {srt_path.stem}\n\n{transcript}\n"
    return f"{transcript}\n"
