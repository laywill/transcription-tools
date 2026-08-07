"""Shared file-or-directory input resolution for the CLI's subcommands."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path


def find_files(
    path: Path,
    extensions: Sequence[str],
    recursive: bool = False,
    label: str = "supported",
) -> list[Path]:
    """Resolve a file or directory input into a sorted list of matching files.

    `label` only shapes the wrong-extension error message, so each subcommand
    can say "Not an .srt file" or "Not an audio or video file" rather than
    leaking the whole extension list at the user.
    """
    suffixes = {ext.lower() for ext in extensions}

    if path.is_file():
        if path.suffix.lower() not in suffixes:
            raise ValueError(f"Not an {label} file: {path}")
        return [path]

    if path.is_dir():
        pattern = "**/*" if recursive else "*"
        matches = (
            p
            for p in path.glob(pattern)
            if p.is_file() and p.suffix.lower() in suffixes
        )
        return sorted(matches)

    raise FileNotFoundError(f"No such file or directory: {path}")
