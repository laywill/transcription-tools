# Known-good transcripts

Reference transcripts for the sample media in `example_input/`, used by the
opt-in end-to-end test (`TRANSCRIPTION_TOOLS_E2E=1 pytest -m e2e`).

One `.txt` file per sample, named after the media file's stem — so
`example_input/sample_speech.mp4` is checked against
`example_input/expected/sample_speech.txt`. A sample with no file here is
skipped rather than failed.

Write them as the transcript should read: a single paragraph of plain text,
no timestamps. The test compares word sequences loosely, so punctuation and
capitalisation differences are tolerated.

This directory is tracked; generated output alongside the sources in
`example_input/` is not.
