# transcription-tools

CLI tools for turning course subtitles and recordings into plain-text or
Markdown transcripts — handy for reading course content offline, or feeding
it to an LLM for summarizing and quizzing.

## Getting Started

### Prerequisites

- Python 3.10+
- A virtual environment (`venv`) — all Python commands below assume one is
  active. Never install dependencies into your system/global Python.

### Installation

```sh
# Clone the repo
git clone https://github.com/laywill/transcription-tools.git
cd transcription-tools

# Create and activate a venv
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the package (editable) with dev dependencies
pip install -e ".[dev]"

# Optional: add the Whisper backend needed by the `transcribe` subcommand
pip install -e ".[dev,transcribe]"
```

The `transcribe` extra is optional so the base install stays small — you only
need it to turn audio/video into text. It decodes media through bundled PyAV,
so there is no separate `ffmpeg` install.

This repo includes a [Dev Container](.devcontainer/devcontainer.json) — open
it in VS Code and choose "Reopen in Container" for a consistent,
pre-configured environment. It provisions Python and creates the venv for
you automatically on container create.

## Usage

The CLI is subcommand-based — `srt-to-text` converts existing subtitles,
`transcribe` creates them from audio or video. More tools are planned (see
[open issues](https://github.com/laywill/transcription-tools/issues)).

### `srt-to-text`

Convert a single `.srt` file to plain text:

```sh
transcription-tools srt-to-text example_input/subtitle_file.srt
# Writes example_input/subtitle_file.txt
```

Convert to Markdown instead:

```sh
transcription-tools srt-to-text example_input/subtitle_file.srt --format md
# Writes example_input/subtitle_file.md
```

Convert every `.srt` file in a directory (add `--recursive`/`-r` to include
subdirectories, `--output`/`-o` to write elsewhere):

```sh
transcription-tools srt-to-text path/to/course/ --format md --recursive --output path/to/transcripts/
```

The input directory's structure is mirrored under the output directory, so
same-named files in different subdirectories do not overwrite each other.

If a file cannot be read or is not valid SRT, it is reported on stderr and the
remaining files are still converted; the command exits non-zero if any file
failed.

### `transcribe`

Turn audio or video into text with [Whisper](https://github.com/openai/whisper),
via [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Needs the
optional extra (`pip install -e ".[transcribe]"`); the model itself is
downloaded on first use and cached.

```sh
transcription-tools transcribe lecture.mp4
# Writes lecture.srt
```

The default output is `.srt` because it is the most useful form: dropped next
to the video, Plex and Jellyfin pick it up as a subtitle track, and the
timestamps let you jump straight to a keyword. Pass `--format txt` or
`--format md` for a flat transcript instead — or chain the two subcommands:

```sh
transcription-tools transcribe course/ --recursive
transcription-tools srt-to-text course/ --recursive --format md
```

Transcribe a whole course tree, writing the transcripts elsewhere:

```sh
transcription-tools transcribe path/to/course/ --recursive --output path/to/transcripts/
```

As with `srt-to-text`, the input tree is mirrored under `--output`, a failing
file is reported on stderr without stopping the rest, and the command exits
non-zero if any file failed. **Files whose output already exists are skipped**,
so an interrupted run over a large library resumes where it left off; pass
`--overwrite` to redo them.

Useful options (`--help` lists them all):

- `--model` (default `turbo`) — `tiny`, `base`, `small`, `medium`,
  `large-v3` or `turbo`. Smaller is faster and less accurate; `turbo` is close
  to `large-v3` at a fraction of the cost.
- `--language` (default: auto-detect) — e.g. `en`. Setting it skips detection
  and avoids the occasional wrong guess on a quiet opening.
- `--device` (default `auto`) — uses CUDA when available, otherwise CPU.
- `--compute-type` (default `int8` on CPU, `float16` on CUDA) — trades speed
  against precision.
- `--model-dir` (default: the Hugging Face cache) — where models download to.
- `--no-vad` — disables the voice-activity filter that skips silent stretches.

Supported inputs are the common audio (`.mp3`, `.m4a`, `.wav`, `.flac`,
`.ogg`, `.opus`, `.aac`, `.wma`) and video (`.mp4`, `.mkv`, `.mov`, `.avi`,
`.webm`, `.m4v`, `.wmv`, `.flv`, `.ts`, `.mpg`, `.mpeg`) container formats.

## Development

This repo runs [MegaLinter](https://megalinter.io/) in CI on every push and pull
request to `main`. Config lives in [.mega-linter.yml](.mega-linter.yml).
[CodeQL](.github/workflows/codeql.yml) scans Python and GitHub Actions
workflows for security issues.

- [.editorconfig](.editorconfig) and [.vscode/settings.json](.vscode/settings.json)
  keep editor formatting consistent (indentation, line endings, trailing whitespace).
- [.gitattributes](.gitattributes) normalizes line endings and marks binary files.
- [pre-commit](https://pre-commit.com/) hooks in
  [.pre-commit-config.yaml](.pre-commit-config.yaml) catch common issues
  locally before you push, including `pyupgrade` to keep syntax current with
  the minimum supported Python version. Install with `pre-commit install`.
- Tests use [pytest](https://pytest.org/) and live in [tests/](tests/). Run
  them with `pytest` (inside your venv, after `pip install -e ".[dev]"`).
  CI runs the suite in [tests.yml](.github/workflows/tests.yml) across every
  currently-supported Python version (3.10-3.14). The suite never downloads a
  model or decodes real audio: `transcribe` is tested against a fake backend.
- The one test that does run Whisper for real is opt-in, since it needs the
  extra installed and downloads a model:
  `TRANSCRIPTION_TOOLS_E2E=1 pytest -m e2e`. It transcribes the sample media in
  [example_input/](example_input/) and compares against the known-good
  transcripts in `example_input/expected/`, and skips itself when either is
  missing.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to file issues and submit
pull requests. Open a pull request using the provided
[PR template](.github/PULL_REQUEST_TEMPLATE.md). CODEOWNERS in
[.github/CODEOWNERS](.github/CODEOWNERS) will be requested for review.
This project follows a [Code of Conduct](CODE_OF_CONDUCT.md). See
[SECURITY.md](SECURITY.md) for how to report vulnerabilities.

## License

Licensed under the [Apache License 2.0](LICENSE).
