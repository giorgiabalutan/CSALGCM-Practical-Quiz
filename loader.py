"""Streaming dataset readers and text normalization/tokenization."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterator
from spellchecker import SpellChecker

from rules import WORD_RE

URL_HTML_RE = re.compile(r"https?://\S+|www\.\S+|<[^>]+>")

SPELL = SpellChecker()

def normalize_text(text: str) -> str:
    """normalize Unicode to NFC and lowercase without stripping Filipino letters (e.g. ñ)."""
    return unicodedata.normalize("NFC", text).lower()


def clean_and_tokenize(text: str) -> Iterator[str]:
    """yield clean lowercase word tokens; strip URLs/HTML tags and retain internal hyphens."""
    if not text:
        return
    text = normalize_text(text)
    text = URL_HTML_RE.sub(" ", text)
    for match in WORD_RE.finditer(text):
        word = match.group(0).strip("-")
        if 2 <= len(word.replace("-", "")) <= 40 and word not in SPELL:
            yield word

def stream_text(filepath: str) -> Iterator[str]:
    """stream text chunks from TXT dumps."""
    path = Path(filepath)

    if path.suffix.lower() != ".txt":
        raise ValueError(f"Unsupported file extension {path.suffix!r}. Expected '.txt'.")

    with path.open("r", encoding="utf-8-sig", errors="replace") as file:
        for line in file:
            if line.strip():
                yield line


def build_vocab(filepath: str, min_count: int = 1,) -> Counter[str]:
    """frequency Counter"""

    if min_count < 1:
        raise ValueError("min_count must be at least 1")
    counts: Counter[str] = Counter()
    for text in stream_text(filepath):
        counts.update(clean_and_tokenize(text))
    if min_count == 1:
        return counts
    return Counter({word: count for word, count in counts.items() if count >= min_count})