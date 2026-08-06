"""Convert .srt subtitle files into plain-text or Markdown transcripts."""

from __future__ import annotations

from pathlib import Path

import pysrt

SUPPORTED_FORMATS = ("txt", "md")


def find_srt_files(path: Path, recursive: bool = False) -> list[Path]:
    """Resolve a file or directory input into a sorted list of .srt files."""
    if path.is_file():
        if path.suffix.lower() != ".srt":
            raise ValueError(f"Not an .srt file: {path}")
        return [path]

    if path.is_dir():
        pattern = "**/*" if recursive else "*"
        srt_files = (
            p for p in path.glob(pattern) if p.is_file() and p.suffix.lower() == ".srt"
        )
        return sorted(srt_files)

    raise FileNotFoundError(f"No such file or directory: {path}")


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
