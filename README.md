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
```

This repo includes a [Dev Container](.devcontainer/devcontainer.json) — open
it in VS Code and choose "Reopen in Container" for a consistent,
pre-configured environment. It provisions Python and creates the venv for
you automatically on container create.

## Usage

The CLI is subcommand-based — `srt-to-text` is the first tool, with more
planned (see [open issues](https://github.com/laywill/transcription-tools/issues)).

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
  currently-supported Python version (3.10-3.14).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to file issues and submit
pull requests. Open a pull request using the provided
[PR template](.github/PULL_REQUEST_TEMPLATE.md). CODEOWNERS in
[.github/CODEOWNERS](.github/CODEOWNERS) will be requested for review.
This project follows a [Code of Conduct](CODE_OF_CONDUCT.md). See
[SECURITY.md](SECURITY.md) for how to report vulnerabilities.

## License

Licensed under the [Apache License 2.0](LICENSE).
