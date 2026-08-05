from pathlib import Path

import pytest

EXAMPLE_SRT = (
    Path(__file__).resolve().parent.parent / "example_input" / "subtitle_file.srt"
)


@pytest.fixture
def example_srt() -> Path:
    assert EXAMPLE_SRT.exists(), f"missing fixture file: {EXAMPLE_SRT}"
    return EXAMPLE_SRT
