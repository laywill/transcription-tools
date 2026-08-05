from pathlib import Path

import pytest

from transcription_tools.srt_to_text import convert_srt, find_srt_files

SIMPLE_SRT = """1
00:00:00,000 --> 00:00:02,000
Hello world.

2
00:00:02,000 --> 00:00:04,000
<i>Italic</i> and plain text.
"""


def _write_srt(tmp_path: Path, name: str, content: str = SIMPLE_SRT) -> Path:
    srt_path = tmp_path / name
    srt_path.write_text(content, encoding="utf-8")
    return srt_path


class TestFindSrtFiles:
    def test_single_file(self, tmp_path: Path) -> None:
        srt_path = _write_srt(tmp_path, "one.srt")
        assert find_srt_files(srt_path) == [srt_path]

    def test_single_file_wrong_extension(self, tmp_path: Path) -> None:
        not_srt = tmp_path / "notes.txt"
        not_srt.write_text("hello", encoding="utf-8")
        with pytest.raises(ValueError, match="Not an .srt file"):
            find_srt_files(not_srt)

    def test_missing_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            find_srt_files(tmp_path / "does-not-exist")

    def test_directory_non_recursive(self, tmp_path: Path) -> None:
        top = _write_srt(tmp_path, "top.srt")
        nested_dir = tmp_path / "nested"
        nested_dir.mkdir()
        _write_srt(nested_dir, "nested.srt")

        assert find_srt_files(tmp_path) == [top]

    def test_directory_recursive(self, tmp_path: Path) -> None:
        top = _write_srt(tmp_path, "top.srt")
        nested_dir = tmp_path / "nested"
        nested_dir.mkdir()
        nested = _write_srt(nested_dir, "nested.srt")

        assert find_srt_files(tmp_path, recursive=True) == sorted([top, nested])

    def test_directory_ignores_non_srt_files(self, tmp_path: Path) -> None:
        _write_srt(tmp_path, "one.srt")
        (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")

        assert len(find_srt_files(tmp_path)) == 1


class TestConvertSrt:
    def test_txt_strips_tags_and_joins(self, tmp_path: Path) -> None:
        srt_path = _write_srt(tmp_path, "one.srt")
        result = convert_srt(srt_path, fmt="txt")
        assert result == "Hello world. Italic and plain text.\n"

    def test_md_adds_heading(self, tmp_path: Path) -> None:
        srt_path = _write_srt(tmp_path, "my-lecture.srt")
        result = convert_srt(srt_path, fmt="md")
        assert result == "# my-lecture\n\nHello world. Italic and plain text.\n"

    def test_default_format_is_txt(self, tmp_path: Path) -> None:
        srt_path = _write_srt(tmp_path, "one.srt")
        assert convert_srt(srt_path) == convert_srt(srt_path, fmt="txt")

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        srt_path = _write_srt(tmp_path, "one.srt")
        with pytest.raises(ValueError, match="Unsupported format"):
            convert_srt(srt_path, fmt="pdf")

    def test_invalid_content_raises(self, tmp_path: Path) -> None:
        srt_path = _write_srt(tmp_path, "prose.srt", "Not subtitles at all.\n")
        with pytest.raises(ValueError, match="Not a valid .srt file"):
            convert_srt(srt_path)

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        srt_path = _write_srt(tmp_path, "empty.srt", "")
        with pytest.raises(ValueError, match="No subtitles found"):
            convert_srt(srt_path)

    def test_real_example_file(self, example_srt: Path) -> None:
        result = convert_srt(example_srt, fmt="txt")
        assert result.startswith("In this video we are going to learn")
        assert "\n\n" not in result
