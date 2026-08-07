"""Real transcription against the sample media in example_input/.

Opt-in, because it needs the `transcribe` extra installed and downloads a
Whisper model on first run:

    TRANSCRIPTION_TOOLS_E2E=1 pytest -m e2e

Set TRANSCRIPTION_TOOLS_E2E_MODEL to try a different model size; the default
is deliberately small so the download and the run stay quick.
"""

import difflib
import importlib.util
import os
import re
from pathlib import Path

import pytest
from conftest import EXAMPLE_INPUT, example_media_files
from transcription_tools import transcribe
from transcription_tools.cli import main
from transcription_tools.srt_to_text import convert_srt

E2E_MODEL = os.environ.get("TRANSCRIPTION_TOOLS_E2E_MODEL", "base")

# Loose on purpose: a model or backend update that shifts punctuation or a
# single word must not turn CI red, while a genuinely broken pipeline (wrong
# audio stream, empty output, garbled text) still fails.
MINIMUM_SIMILARITY = 0.75

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.environ.get("TRANSCRIPTION_TOOLS_E2E") != "1",
        reason="set TRANSCRIPTION_TOOLS_E2E=1 to run real transcription",
    ),
]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower())


def _similarity(actual: str, expected: str) -> float:
    return difflib.SequenceMatcher(None, _words(actual), _words(expected)).ratio()


@pytest.fixture(scope="module", autouse=True)
def _require_media_and_backend():
    # Guard before anything downloads a model, and skip rather than fail so
    # `pytest -m e2e` is safe to run in a checkout without the extra or media.
    if not example_media_files():
        pytest.skip(f"no sample audio/video in {EXAMPLE_INPUT}")
    if importlib.util.find_spec("faster_whisper") is None:
        pytest.skip(f"transcribe extra not installed: {transcribe.INSTALL_HINT}")


@pytest.fixture(scope="module")
def model():
    return transcribe.load_model(model=E2E_MODEL)


def test_transcript_matches_known_good(
    model, example_media: Path, expected_transcript: str
) -> None:
    segments, language = transcribe.transcribe_media(model, example_media)
    actual = transcribe.format_transcript(segments, fmt="txt")

    assert language == "en"
    similarity = _similarity(actual, expected_transcript)
    assert similarity >= MINIMUM_SIMILARITY, (
        f"{example_media.name}: transcript similarity {similarity:.2f} below "
        f"{MINIMUM_SIMILARITY}\n  expected: {expected_transcript.strip()}\n"
        f"  actual:   {actual.strip()}"
    )


def test_cli_writes_srt_that_srt_to_text_can_read(
    example_media: Path, expected_transcript: str, tmp_path: Path
) -> None:
    destination = tmp_path / f"{example_media.stem}.srt"

    exit_code = main(
        [
            "transcribe",
            str(example_media),
            "--model",
            E2E_MODEL,
            "--output",
            str(destination),
        ]
    )

    assert exit_code == 0
    similarity = _similarity(convert_srt(destination), expected_transcript)
    assert similarity >= MINIMUM_SIMILARITY
