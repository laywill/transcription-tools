"""Shared transcript-text joining, used by both srt-to-text and transcribe."""

from __future__ import annotations

import re
from collections.abc import Iterable

# Matches whitespace between a sentence-ending punctuation mark and the
# capitalised start of the next sentence. This is a heuristic, not a full
# sentence tokenizer: it can false-split abbreviations like "Dr. Smith", a
# tradeoff accepted in favour of readability (see issue #8).
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def join_sentences(fragments: Iterable[str], newlines: bool = False) -> str:
    """Join non-empty fragments into a transcript, one sentence per line if set."""
    text = " ".join(fragment for fragment in fragments if fragment)
    if newlines:
        text = _SENTENCE_BOUNDARY.sub("\n", text)
    return text
