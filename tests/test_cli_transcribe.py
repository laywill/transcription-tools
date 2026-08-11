# Tests taking a fixture as an argument is the pytest idiom, not shadowing.
# pylint: disable=redefined-outer-name

from pathlib import Path

import pytest
from transcription_tools import transcribe
from transcription_tools.cli import main

EXPECTED_SRT = (
    "1\n00:00:00,000 --> 00:00:01,500\nHello world.\n\n"
    "2\n00:00:01,500 --> 00:00:03,250\nSecond line.\n\n"
)


def _touch_media(directory: Path, name: str) -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not really media")
    return path


class _StubBackend:  # pylint: disable=too-few-public-methods
    """Patches load_model so the CLI runs with no model download or real audio.

    `loaded` records the keyword arguments the CLI passed to load_model, which
    is how the option-plumbing test checks them.
    """

    def __init__(self, monkeypatch, model_factory):
        self._monkeypatch = monkeypatch
        self._model_factory = model_factory
        self.loaded: dict = {}

    def install(self, **model_kwargs):
        model = self._model_factory(**model_kwargs)

        def fake_load_model(**kwargs):
            self.loaded.update(kwargs)
            return model

        self._monkeypatch.setattr(transcribe, "load_model", fake_load_model)
        return model


@pytest.fixture
def stub_backend(monkeypatch, fake_whisper_model):
    return _StubBackend(monkeypatch, fake_whisper_model)


def test_single_file_defaults_to_srt(tmp_path, stub_backend) -> None:
    media = _touch_media(tmp_path, "lecture.mp4")
    stub_backend.install()

    exit_code = main(["transcribe", str(media)])

    assert exit_code == 0
    assert (tmp_path / "lecture.srt").read_text(encoding="utf-8") == EXPECTED_SRT


def test_single_file_markdown_format(tmp_path, stub_backend) -> None:
    media = _touch_media(tmp_path, "lecture.mp4")
    stub_backend.install()

    exit_code = main(["transcribe", str(media), "--format", "md"])

    assert exit_code == 0
    assert (tmp_path / "lecture.md").read_text(encoding="utf-8") == (
        "# lecture\n\nHello world. Second line.\n"
    )


def test_single_file_explicit_output(tmp_path, stub_backend) -> None:
    media = _touch_media(tmp_path, "lecture.m4a")
    output_path = tmp_path / "custom" / "transcript.txt"
    stub_backend.install()

    exit_code = main(
        ["transcribe", str(media), "--format", "txt", "--output", str(output_path)]
    )

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == "Hello world. Second line.\n"


def test_recursive_output_dir_preserves_subdirectories(tmp_path, stub_backend) -> None:
    input_dir = tmp_path / "course"
    for module in ("module-1", "module-2"):
        _touch_media(input_dir / module, "intro.mp4")
    output_dir = tmp_path / "transcripts"
    stub_backend.install()

    exit_code = main(
        ["transcribe", str(input_dir), "--recursive", "--output", str(output_dir)]
    )

    assert exit_code == 0
    assert (output_dir / "module-1" / "intro.srt").exists()
    assert (output_dir / "module-2" / "intro.srt").exists()


def test_directory_input_output_existing_file_errors(tmp_path, stub_backend) -> None:
    input_dir = tmp_path / "course"
    _touch_media(input_dir, "one.mp4")
    output_file = tmp_path / "already-a-file.srt"
    output_file.write_text("keep me", encoding="utf-8")
    stub_backend.install()

    exit_code = main(["transcribe", str(input_dir), "--output", str(output_file)])

    assert exit_code == 1
    assert output_file.read_text(encoding="utf-8") == "keep me"


def test_missing_input_returns_error_code(tmp_path, capsys) -> None:
    exit_code = main(["transcribe", str(tmp_path / "missing.mp4")])

    assert exit_code == 1
    assert "error" in capsys.readouterr().err


def test_directory_without_media_returns_error_code(tmp_path, capsys) -> None:
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")

    exit_code = main(["transcribe", str(tmp_path)])

    assert exit_code == 1
    assert "no audio or video files" in capsys.readouterr().err


def test_batch_continues_past_failing_file(tmp_path, stub_backend, capsys) -> None:
    _touch_media(tmp_path, "bad.mp4")
    _touch_media(tmp_path, "good.mp4")
    stub_backend.install(fail_on=["bad.mp4"])

    exit_code = main(["transcribe", str(tmp_path)])

    assert exit_code == 1
    assert (tmp_path / "good.srt").exists()
    assert not (tmp_path / "bad.srt").exists()
    assert "bad.mp4" in capsys.readouterr().err


def test_existing_output_is_skipped(tmp_path, stub_backend, capsys) -> None:
    media = _touch_media(tmp_path, "lecture.mp4")
    (tmp_path / "lecture.srt").write_text("already done\n", encoding="utf-8")
    model = stub_backend.install()

    exit_code = main(["transcribe", str(media)])

    assert exit_code == 0
    assert (tmp_path / "lecture.srt").read_text(encoding="utf-8") == "already done\n"
    assert model.calls == []
    assert "Skipping" in capsys.readouterr().out


def test_overwrite_redoes_existing_output(tmp_path, stub_backend) -> None:
    media = _touch_media(tmp_path, "lecture.mp4")
    (tmp_path / "lecture.srt").write_text("already done\n", encoding="utf-8")
    stub_backend.install()

    exit_code = main(["transcribe", str(media), "--overwrite"])

    assert exit_code == 0
    assert (tmp_path / "lecture.srt").read_text(encoding="utf-8") == EXPECTED_SRT


def test_model_options_are_passed_through(tmp_path, stub_backend) -> None:
    media = _touch_media(tmp_path, "lecture.mp4")
    model = stub_backend.install()
    model_dir = tmp_path / "models"

    exit_code = main(
        [
            "transcribe",
            str(media),
            "--model",
            "tiny",
            "--language",
            "fr",
            "--device",
            "cpu",
            "--compute-type",
            "float32",
            "--model-dir",
            str(model_dir),
            "--no-vad",
        ]
    )

    assert exit_code == 0
    assert stub_backend.loaded == {
        "model": "tiny",
        "device": "cpu",
        "compute_type": "float32",
        "model_dir": model_dir,
    }
    assert model.calls == [{"path": str(media), "language": "fr", "vad_filter": False}]


def test_missing_backend_reports_install_hint(tmp_path, monkeypatch, capsys) -> None:
    _touch_media(tmp_path, "lecture.mp4")

    def raise_missing(**_kwargs):
        raise transcribe.MissingBackendError("faster-whisper is not installed")

    monkeypatch.setattr(transcribe, "load_model", raise_missing)

    exit_code = main(["transcribe", str(tmp_path)])

    assert exit_code == 1
    assert "faster-whisper is not installed" in capsys.readouterr().err


def test_unloadable_model_reports_error(tmp_path, monkeypatch, capsys) -> None:
    _touch_media(tmp_path, "lecture.mp4")

    def raise_value_error(**_kwargs):
        raise ValueError("invalid model size")

    monkeypatch.setattr(transcribe, "load_model", raise_value_error)

    exit_code = main(["transcribe", str(tmp_path), "--model", "nonsense"])

    assert exit_code == 1
    assert "could not load model 'nonsense'" in capsys.readouterr().err
