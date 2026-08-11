# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment

All Python commands must run inside the project venv (`.venv`), never the
system/global Python.

```sh
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Commands

```sh
pytest                                   # full suite (coverage is built in — see below)
pytest tests/test_cli.py                 # one file
pytest tests/test_cli.py::test_single_file_txt_default   # one test
pytest --no-cov                          # skip the coverage gate while iterating

pre-commit run --all-files               # local lint pass before pushing
transcription-tools srt-to-text example_input/subtitle_file.srt --format md

pip install -e ".[dev,transcribe]"       # adds the optional Whisper backend
TRANSCRIPTION_TOOLS_E2E=1 pytest -m e2e  # opt-in: real model, real media
```

Coverage flags (`--cov --cov-branch --cov-report=term-missing
--cov-fail-under=90`) live in `pyproject.toml`'s `addopts`, deliberately, so a
bare `pytest` behaves identically locally and in CI. A test run failing at
"Required test coverage of 90% not reached" is the gate, not a broken suite.

CI (`.github/workflows/tests.yml`) runs `pytest` across Python 3.10–3.14, so
keep code compatible with 3.10 (pre-commit's `pyupgrade --py310-plus` enforces
the syntax floor). MegaLinter and CodeQL also run on every push/PR to `main`.

## Architecture

A single subcommand-based CLI (`transcription-tools`), packaged with hatchling
from `src/transcription_tools/`, entry point `transcription_tools.cli:main`.
`srt-to-text` and `transcribe` are the current subcommands; more are planned,
so the structure is built for adding tools rather than for one tool.

The separation to preserve when adding a subcommand:

- **`srt_to_text.py`** / **`transcribe.py`** — pure logic, no I/O to
  stdout/stderr and no exit codes. `convert_srt()` and `format_transcript()`
  return strings; everything raises (`ValueError`, `FileNotFoundError`) rather
  than printing.
- **`file_discovery.py`** — `find_files()` resolves a file-or-directory input
  into a sorted list, shared by both subcommands' `find_*_files()` wrappers.
  Its `label` argument only shapes the wrong-extension error message.
- **`cli.py`** — argparse wiring plus all user-facing I/O. Each subcommand adds
  a parser and a `set_defaults(handler=...)` function taking
  `argparse.Namespace` and returning an int exit code; `main()` just dispatches
  to `args.handler`.

`transcribe.py` imports `faster_whisper` **lazily inside `load_model()`** and
converts an `ImportError` into `MissingBackendError`. That is what keeps the
backend an optional extra (`pip install -e ".[transcribe]"`) and lets the whole
suite run offline: tests inject a fake model object, and `Segment` exists so
nothing outside `load_model()`/`transcribe_media()` touches the backend's
types. Do not move that import to module scope.

`transcribe` deliberately diverges from `srt-to-text` in two places, both
because transcription is slow: the model is loaded once before the batch (so a
missing backend or bad model name fails before any work), and existing outputs
are skipped unless `--overwrite`, so an interrupted run resumes.

Two behaviours in `cli.py` that tests pin down and are easy to break:

- **Batch resilience** — both handlers catch per-file errors, report them on
  stderr, keep going with the rest, and return exit code 1 if *any* file
  failed. Do not let one bad file abort the run.
- **Output path mirroring** — `_resolve_destination` reproduces the input tree
  under `--output` so same-named files in different subdirectories (common in
  course exports: `module-1/intro.srt`, `module-2/intro.srt`) do not overwrite
  each other. `--output` as a plain file path is only honoured for single-file
  input.

## Conventions

Docstrings are written for non-obvious behaviour only, not on every module and
function — pylint's `missing-*-docstring` checks are disabled in
`pyproject.toml` to match. Comments in this codebase explain *why* a decision
was made (see the `PRE_COMMANDS` block in `.mega-linter.yml` or the `addopts`
note in `pyproject.toml`); follow that style rather than restating the code.

Tests use `tmp_path` and build their own SRT strings; `tests/conftest.py`
exposes an `example_srt` fixture pointing at `example_input/subtitle_file.srt`,
plus a `FakeWhisperModel` so transcription tests need neither a model download
nor real audio. Generated `.txt`/`.md`/`.srt` output under `example_input/` is
gitignored (the committed `subtitle_file.srt` is an input, not output).

`tests/test_transcribe_e2e.py` is the exception: it runs the real backend
against sample media in `example_input/`, and skips unless
`TRANSCRIPTION_TOOLS_E2E=1` and both the media and its
`example_input/expected/<stem>.txt` transcript exist. It matches loosely
(word-overlap ratio) on purpose — a model update changing punctuation must not
turn CI red.
