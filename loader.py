"""Streaming dataset readers and text normalization/tokenization."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterator

from rules import WORD_RE

# prevent _csv.Error on large scraped text cells in CSV/TSV datasets.
csv.field_size_limit(min(sys.maxsize, 2**30))

URL_HTML_RE = re.compile(r"https?://\S+|www\.\S+|<[^>]+>")
SQL_STRING_LITERAL_RE = re.compile(r"'((?:[^'\\]|\\.|'')*)'")


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
        if 2 <= len(word.replace("-", "")) <= 40:
            yield word


def _first_nonempty_string(value: object) -> str:
    """fallback extractor for JSON/JSONL records when no explicit field name is provided."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content", "body", "sentence", "message"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        return " ".join(v for v in value.values() if isinstance(v, str))
    if isinstance(value, list):
        return " ".join(v for v in value if isinstance(v, str))
    return ""


def _validate_sqlite_identifier(identifier: str) -> str:
    """allow simple SQLite identifiers only; prevents SQL identifier injection."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ValueError(f"Invalid SQLite table/column identifier: {identifier!r}")
    return f'"{identifier}"'


def stream_text(
    filepath: str,
    text_column: str | None = None,
    table_name: str | None = None,
) -> Iterator[str]:
    """stream text chunks from TXT, CSV, TSV, JSONL, JSON, SQLite, or SQL dumps."""
    path = Path(filepath)
    ext = path.suffix.lower()

    if ext in {".txt", ".log"}:
        with path.open("r", encoding="utf-8-sig", errors="replace") as file:
            for line in file:
                if line.strip():
                    yield line
        return

    if ext in {".csv", ".tsv"}:
        delimiter = "\t" if ext == ".tsv" else ","
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as file:
            if text_column:
                reader = csv.DictReader(file, delimiter=delimiter)
                if not reader.fieldnames or text_column not in reader.fieldnames:
                    raise ValueError(
                        f"Column {text_column!r} not found. Available columns: {reader.fieldnames}"
                    )
                for row in reader:
                    val = row.get(text_column)
                    if val:
                        yield val
            else:
                # safe fallback: read all cells in every row so ID columns or
                # headerless CSVs never result in 0 extracted tokens.
                raw_reader = csv.reader(file, delimiter=delimiter)
                for row in raw_reader:
                    if row:
                        yield " ".join(row)
        return

    if ext == ".jsonl":
        with path.open("r", encoding="utf-8-sig", errors="replace") as file:
            for line in file:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = (
                    obj.get(text_column, "")
                    if (text_column and isinstance(obj, dict))
                    else _first_nonempty_string(obj)
                )
                if isinstance(text, str) and text:
                    yield text
        return

    if ext == ".json":
        with path.open("r", encoding="utf-8-sig", errors="replace") as file:
            data = json.load(file)
        records = data if isinstance(data, list) else [data]
        for obj in records:
            text = (
                obj.get(text_column, "")
                if (text_column and isinstance(obj, dict))
                else _first_nonempty_string(obj)
            )
            if isinstance(text, str) and text:
                yield text
        return

    if ext in {".db", ".sqlite", ".sqlite3"}:
        connection = sqlite3.connect(path)
        try:
            if table_name is None:
                row = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name LIMIT 1"
                ).fetchone()
                if row is None:
                    raise ValueError("SQLite database contains no tables")
                table_name = row[0]
            quoted_table = _validate_sqlite_identifier(table_name)

            if text_column:
                quoted_col = _validate_sqlite_identifier(text_column)
                query = f"SELECT {quoted_col} FROM {quoted_table}"
            else:
                query = f"SELECT * FROM {quoted_table}"

            cursor = connection.execute(query)
            while True:
                rows = cursor.fetchmany(2000)
                if not rows:
                    break
                for row in rows:
                    yield " ".join(str(cell) for cell in row if isinstance(cell, str))
        finally:
            connection.close()
        return

    if ext == ".sql":
        # emergency fallback if the dataset is a raw .sql dump with INSERT statements.
        with path.open("r", encoding="utf-8-sig", errors="replace") as file:
            for line in file:
                if "INSERT INTO" in line.upper() or line.lstrip().startswith("("):
                    for match in SQL_STRING_LITERAL_RE.finditer(line):
                        yield match.group(1)
        return

    raise ValueError(
        f"Unsupported file extension {ext!r}. Supported: .txt, .log, .csv, .tsv, "
        ".jsonl, .json, .db, .sqlite, .sqlite3, .sql"
    )


def build_vocab(
    filepath: str,
    min_count: int = 1,
    text_column: str | None = None,
    table_name: str | None = None,
) -> Counter[str]:
    """frequency Counter"""
    if min_count < 1:
        raise ValueError("min_count must be at least 1")
    counts: Counter[str] = Counter()
    for text in stream_text(filepath, text_column=text_column, table_name=table_name):
        counts.update(clean_and_tokenize(text))
    if min_count == 1:
        return counts
    return Counter({word: count for word, count in counts.items() if count >= min_count})