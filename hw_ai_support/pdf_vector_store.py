"""Small persistent TF-IDF vector index for local ERPNext PDF references.

The index uses SQLite and sparse Python vectors so the demo needs no external
vector database service. PDF chunks and their vectors are rebuilt when the
source file changes.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import threading
from contextlib import closing
from typing import Any

from pypdf import PdfReader


TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
CHUNK_SIZE = 1100
CHUNK_OVERLAP = 160
_INDEX_LOCK = threading.Lock()


def _tokens(text: str) -> list[str]:
    return [word.lower() for word in TOKEN_RE.findall(text or "") if len(word) > 1]


def _pdf_chunks(path: Path) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    reader = PdfReader(str(path))
    for page_number, page in enumerate(reader.pages, start=1):
        text = re.sub(r"\s+", " ", page.extract_text() or "").strip()
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            if end < len(text):
                boundary = text.rfind(". ", start + CHUNK_SIZE // 2, end)
                if boundary > start:
                    end = boundary + 1
            part = text[start:end].strip()
            if len(_tokens(part)) >= 8:
                chunks.append({"page": page_number, "text": part})
            if end >= len(text):
                break
            start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def _source_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _build_index(path: Path, db_path: Path, digest: str) -> None:
    chunks = _pdf_chunks(path)
    if not chunks:
        raise ValueError(f"No extractable text found in ERPNext PDF: {path}")

    counters = [Counter(_tokens(chunk["text"])) for chunk in chunks]
    document_frequency: Counter[str] = Counter()
    for counts in counters:
        document_frequency.update(counts.keys())
    total = len(chunks)
    idf = {term: math.log(1 + total / (1 + count)) + 1 for term, count in document_frequency.items()}

    db_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = db_path.with_name(f"{db_path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
    temporary.unlink(missing_ok=True)
    with closing(sqlite3.connect(temporary)) as connection:
        with connection:
            connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("CREATE TABLE chunks (id INTEGER PRIMARY KEY, page INTEGER NOT NULL, text TEXT NOT NULL, vector TEXT NOT NULL)")
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                [("source_digest", digest), ("idf", json.dumps(idf, ensure_ascii=False))],
            )
            rows = []
            for index, (chunk, counts) in enumerate(zip(chunks, counters)):
                total_terms = max(1, sum(counts.values()))
                vector = {term: (count / total_terms) * idf[term] for term, count in counts.items()}
                rows.append((index, chunk["page"], chunk["text"], json.dumps(vector, ensure_ascii=False)))
            connection.executemany("INSERT INTO chunks(id, page, text, vector) VALUES (?, ?, ?, ?)", rows)
    temporary.replace(db_path)


def retrieve_pdf_chunks(
    question: str,
    *,
    pdf_path: str | Path,
    db_path: str | Path,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Return the most similar document chunks using cosine similarity."""
    source = Path(pdf_path)
    if not source.is_file():
        return []
    database = Path(db_path)
    digest = _source_digest(source)
    current_digest = None
    with _INDEX_LOCK:
        if database.is_file():
            try:
                with closing(sqlite3.connect(database)) as connection:
                    row = connection.execute("SELECT value FROM metadata WHERE key='source_digest'").fetchone()
                    current_digest = row[0] if row else None
            except sqlite3.DatabaseError:
                current_digest = None
        if digest != current_digest:
            _build_index(source, database, digest)

    query_counts = Counter(_tokens(question))
    if not query_counts:
        return []
    with closing(sqlite3.connect(database)) as connection:
        idf_row = connection.execute("SELECT value FROM metadata WHERE key='idf'").fetchone()
        idf = json.loads(idf_row[0]) if idf_row else {}
        q_total = max(1, sum(query_counts.values()))
        query = {term: (count / q_total) * idf.get(term, 0.0) for term, count in query_counts.items()}
        q_norm = math.sqrt(sum(value * value for value in query.values()))
        if not q_norm:
            return []
        scored = []
        for page, text, raw_vector in connection.execute("SELECT page, text, vector FROM chunks"):
            vector = json.loads(raw_vector)
            norm = math.sqrt(sum(value * value for value in vector.values()))
            if not norm:
                continue
            score = sum(value * vector.get(term, 0.0) for term, value in query.items()) / (q_norm * norm)
            if score >= 0.035:
                scored.append((score, page, text))
    scored.sort(key=lambda row: row[0], reverse=True)
    return [
        {"source": source.name, "page": page, "score": round(score, 4), "text": text}
        for score, page, text in scored[:limit]
    ]
