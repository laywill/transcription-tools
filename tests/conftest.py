from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from transcription_tools.transcribe import MEDIA_EXTENSIONS

EXAMPLE_INPUT = Path(__file__).resolve().parent.parent / "example_input"
EXAMPLE_SRT = EXAMPLE_INPUT / "subtitle_file.srt"
EXPECTED_TRANSCRIPTS = EXAMPLE_INPUT / "expected"

DEFAULT_FAKE_SEGMENTS = (
    (0.0, 1.5, " Hello world."),
    (1.5, 3.25, " Second line."),
)


@dataclass(frozen=True)
class FakeSegment:
    start: float
    end: float
    text: str


class FakeWhisperModel:
    """Stand-in for faster_whisper.WhisperModel.

    Keeps the suite offline and instant: no model download, no audio decoding.
    `fail_on` takes file names that should raise, which is how the batch
    resilience tests get a "bad" file without crafting broken media.
    """

    def __init__(self, segments=None, language="en", fail_on=()):
        if segments is None:
            segments = [FakeSegment(*values) for values in DEFAULT_FAKE_SEGMENTS]
        self.segments = list(segments)
        self.language = language
        self.fail_on = set(fail_on)
        self.calls = []

    def transcribe(self, path, language=None, vad_filter=True):
        self.calls.append(
            {"path": path, "language": language, "vad_filter": vad_filter}
        )
        if Path(path).name in self.fail_on:
            raise RuntimeError("could not decode media")
        info = SimpleNamespace(
            language=language or self.language, language_probability=0.99
        )
        # The real backend decodes lazily and hands back a generator.
        return iter(self.segments), info


def example_media_files() -> list[Path]:
    """Sample audio/video the repo carries, if any; used by the e2e tests."""
    if not EXAMPLE_INPUT.is_dir():
        return []
    return sorted(
        path
        for path in EXAMPLE_INPUT.glob("*")
        if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
    )


@pytest.fixture
def example_srt() -> Path:
    assert EXAMPLE_SRT.exists(), f"missing fixture file: {EXAMPLE_SRT}"
    return EXAMPLE_SRT


# Parametrised over whatever sample media the repo happens to carry, with a
# None placeholder so the e2e tests skip cleanly rather than fail to collect
# when there is none yet.
@pytest.fixture(
    params=example_media_files() or [None],
    ids=lambda path: path.name if path else "none",
)
def example_media(request) -> Path:
    if request.param is None:
        pytest.skip(f"no sample audio/video in {EXAMPLE_INPUT}")
    return request.param


@pytest.fixture
def expected_transcript(example_media: Path) -> str:
    path = EXPECTED_TRANSCRIPTS / f"{example_media.stem}.txt"
    if not path.exists():
        pytest.skip(f"no known-good transcript at {path}")
    return path.read_text(encoding="utf-8")


@pytest.fixture
def fake_segment():
    return FakeSegment


@pytest.fixture
def fake_whisper_model():
    return FakeWhisperModel
