import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from transcription_tools.srt_to_text import convert_srt
from transcription_tools.transcribe import (
    DEFAULT_MODEL,
    MissingBackendError,
    Segment,
    find_media_files,
    format_transcript,
    load_model,
    resolve_runtime,
    transcribe_media,
)

SEGMENTS = [
    Segment(0.0, 1.5, "Hello world."),
    Segment(1.5, 3.25, "Second line."),
]


def _touch(directory: Path, name: str) -> Path:
    path = directory / name
    path.write_bytes(b"not really media")
    return path


class TestFindMediaFiles:
    def test_single_audio_file(self, tmp_path: Path) -> None:
        media = _touch(tmp_path, "lecture.mp3")
        assert find_media_files(media) == [media]

    def test_single_video_file(self, tmp_path: Path) -> None:
        media = _touch(tmp_path, "lecture.MKV")
        assert find_media_files(media) == [media]

    def test_single_file_wrong_extension(self, tmp_path: Path) -> None:
        notes = _touch(tmp_path, "notes.txt")
        with pytest.raises(ValueError, match="Not an audio or video file"):
            find_media_files(notes)

    def test_missing_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            find_media_files(tmp_path / "does-not-exist")

    def test_directory_ignores_other_files(self, tmp_path: Path) -> None:
        media = _touch(tmp_path, "lecture.mp4")
        _touch(tmp_path, "lecture.srt")
        _touch(tmp_path, "notes.txt")

        assert find_media_files(tmp_path) == [media]

    def test_directory_non_recursive(self, tmp_path: Path) -> None:
        top = _touch(tmp_path, "top.mp4")
        nested_dir = tmp_path / "module-1"
        nested_dir.mkdir()
        _touch(nested_dir, "nested.mp4")

        assert find_media_files(tmp_path) == [top]

    def test_directory_recursive(self, tmp_path: Path) -> None:
        top = _touch(tmp_path, "top.mp4")
        nested_dir = tmp_path / "module-1"
        nested_dir.mkdir()
        nested = _touch(nested_dir, "nested.m4a")

        assert find_media_files(tmp_path, recursive=True) == sorted([top, nested])


class TestResolveRuntime:
    def test_auto_without_cuda_is_cpu_int8(self) -> None:
        assert resolve_runtime("auto", None, cuda_available=False) == ("cpu", "int8")

    def test_auto_with_cuda_is_float16(self) -> None:
        assert resolve_runtime("auto", None, cuda_available=True) == (
            "cuda",
            "float16",
        )

    def test_explicit_device_is_respected(self) -> None:
        assert resolve_runtime("cpu", None, cuda_available=True) == ("cpu", "int8")

    def test_explicit_compute_type_is_respected(self) -> None:
        assert resolve_runtime("cpu", "float32", cuda_available=False) == (
            "cpu",
            "float32",
        )


class TestFormatTranscript:
    def test_srt_is_timestamped(self) -> None:
        result = format_transcript(SEGMENTS, fmt="srt")
        assert result == (
            "1\n00:00:00,000 --> 00:00:01,500\nHello world.\n\n"
            "2\n00:00:01,500 --> 00:00:03,250\nSecond line.\n\n"
        )

    def test_srt_round_trips_through_srt_to_text(self, tmp_path: Path) -> None:
        srt_path = tmp_path / "lecture.srt"
        srt_path.write_text(format_transcript(SEGMENTS, fmt="srt"), encoding="utf-8")

        assert convert_srt(srt_path) == "Hello world. Second line.\n"

    def test_txt_joins_segments(self) -> None:
        assert format_transcript(SEGMENTS, fmt="txt") == "Hello world. Second line.\n"

    def test_md_adds_heading(self) -> None:
        result = format_transcript(SEGMENTS, fmt="md", title="my-lecture")
        assert result == "# my-lecture\n\nHello world. Second line.\n"

    def test_txt_skips_empty_segments(self) -> None:
        segments = [*SEGMENTS, Segment(3.25, 4.0, "   ")]
        assert format_transcript(segments, fmt="txt") == "Hello world. Second line.\n"

    def test_unsupported_format_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported format"):
            format_transcript(SEGMENTS, fmt="pdf")


class TestTranscribeMedia:
    def test_returns_segments_and_language(self, tmp_path, fake_whisper_model) -> None:
        model = fake_whisper_model()
        segments, language = transcribe_media(model, tmp_path / "lecture.mp4")

        assert language == "en"
        assert [s.text for s in segments] == ["Hello world.", "Second line."]
        assert segments[0] == Segment(0.0, 1.5, "Hello world.")

    def test_passes_language_and_vad_through(self, tmp_path, fake_whisper_model):
        model = fake_whisper_model()
        media = tmp_path / "lecture.mp4"

        transcribe_media(model, media, language="fr", vad_filter=False)

        assert model.calls == [
            {"path": str(media), "language": "fr", "vad_filter": False}
        ]

    def test_no_speech_raises(self, tmp_path, fake_whisper_model) -> None:
        model = fake_whisper_model(segments=[])
        with pytest.raises(ValueError, match="No speech detected"):
            transcribe_media(model, tmp_path / "silent.mp4")

    def test_unknown_language_falls_back(self, tmp_path, fake_whisper_model) -> None:
        model = fake_whisper_model(language=None)
        _, language = transcribe_media(model, tmp_path / "lecture.mp4")
        assert language == "unknown"

    def test_decode_error_propagates(self, tmp_path, fake_whisper_model) -> None:
        model = fake_whisper_model(fail_on=["bad.mp4"])
        with pytest.raises(RuntimeError, match="could not decode"):
            transcribe_media(model, tmp_path / "bad.mp4")


class TestLoadModel:
    def test_missing_backend_raises_with_install_hint(self, monkeypatch) -> None:
        # None in sys.modules makes the import fail even where the extra is
        # installed, so the test result does not depend on the environment.
        monkeypatch.setitem(sys.modules, "ctranslate2", None)
        monkeypatch.setitem(sys.modules, "faster_whisper", None)

        with pytest.raises(MissingBackendError, match=r'pip install -e ".\[transcribe'):
            load_model()

    def test_builds_model_with_resolved_runtime(self, monkeypatch, tmp_path) -> None:
        built: dict[str, Any] = {}

        class FakeWhisperModelClass:  # pylint: disable=too-few-public-methods
            def __init__(self, model, device, compute_type, download_root):
                built.update(
                    model=model,
                    device=device,
                    compute_type=compute_type,
                    download_root=download_root,
                )

        # Typed as Any so the type checker accepts the stubbed attributes.
        fake_ctranslate2: Any = ModuleType("ctranslate2")
        fake_ctranslate2.get_cuda_device_count = lambda: 0
        fake_faster_whisper: Any = ModuleType("faster_whisper")
        fake_faster_whisper.WhisperModel = FakeWhisperModelClass
        monkeypatch.setitem(sys.modules, "ctranslate2", fake_ctranslate2)
        monkeypatch.setitem(sys.modules, "faster_whisper", fake_faster_whisper)

        model = load_model("tiny", model_dir=tmp_path)

        assert isinstance(model, FakeWhisperModelClass)
        assert built == {
            "model": "tiny",
            "device": "cpu",
            "compute_type": "int8",
            "download_root": str(tmp_path),
        }

    def test_defaults_to_cuda_and_no_download_root(self, monkeypatch) -> None:
        built: dict[str, Any] = {}

        def fake_whisper_model_class(model, device, compute_type, download_root):
            built.update(
                model=model,
                device=device,
                compute_type=compute_type,
                download_root=download_root,
            )

        fake_ctranslate2: Any = ModuleType("ctranslate2")
        fake_ctranslate2.get_cuda_device_count = lambda: 1
        fake_faster_whisper: Any = ModuleType("faster_whisper")
        fake_faster_whisper.WhisperModel = fake_whisper_model_class
        monkeypatch.setitem(sys.modules, "ctranslate2", fake_ctranslate2)
        monkeypatch.setitem(sys.modules, "faster_whisper", fake_faster_whisper)

        load_model()

        assert built == {
            "model": DEFAULT_MODEL,
            "device": "cuda",
            "compute_type": "float16",
            "download_root": None,
        }
