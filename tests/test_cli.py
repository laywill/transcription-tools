from pathlib import Path

from transcription_tools.cli import main

SIMPLE_SRT = """1
00:00:00,000 --> 00:00:02,000
Hello world.
"""


def _write_srt(tmp_path: Path, name: str) -> Path:
    srt_path = tmp_path / name
    srt_path.write_text(SIMPLE_SRT, encoding="utf-8")
    return srt_path


def test_single_file_txt_default(tmp_path: Path) -> None:
    srt_path = _write_srt(tmp_path, "lecture.srt")

    exit_code = main(["srt-to-text", str(srt_path)])

    assert exit_code == 0
    output_path = tmp_path / "lecture.txt"
    assert output_path.read_text(encoding="utf-8") == "Hello world.\n"


def test_single_file_markdown_format(tmp_path: Path) -> None:
    srt_path = _write_srt(tmp_path, "lecture.srt")

    exit_code = main(["srt-to-text", str(srt_path), "--format", "md"])

    assert exit_code == 0
    output_path = tmp_path / "lecture.md"
    assert output_path.read_text(encoding="utf-8") == "# lecture\n\nHello world.\n"


def test_single_file_explicit_output(tmp_path: Path) -> None:
    srt_path = _write_srt(tmp_path, "lecture.srt")
    output_path = tmp_path / "custom" / "transcript.txt"

    exit_code = main(["srt-to-text", str(srt_path), "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.read_text(encoding="utf-8") == "Hello world.\n"


def test_directory_input_converts_all(tmp_path: Path) -> None:
    _write_srt(tmp_path, "one.srt")
    _write_srt(tmp_path, "two.srt")

    exit_code = main(["srt-to-text", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "one.txt").exists()
    assert (tmp_path / "two.txt").exists()


def test_directory_input_with_output_dir(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    _write_srt(input_dir, "one.srt")
    output_dir = tmp_path / "output"

    exit_code = main(["srt-to-text", str(input_dir), "--output", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "one.txt").exists()


def test_directory_recursive_flag(tmp_path: Path) -> None:
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    _write_srt(nested_dir, "nested.srt")

    non_recursive_exit_code = main(["srt-to-text", str(tmp_path)])
    assert non_recursive_exit_code == 1

    recursive_exit_code = main(["srt-to-text", str(tmp_path), "--recursive"])
    assert recursive_exit_code == 0
    assert (nested_dir / "nested.txt").exists()


def test_missing_input_returns_error_code(tmp_path: Path, capsys) -> None:
    exit_code = main(["srt-to-text", str(tmp_path / "missing.srt")])

    assert exit_code == 1
    assert "error" in capsys.readouterr().err
