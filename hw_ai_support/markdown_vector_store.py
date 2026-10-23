"""Small lexical TF-IDF retriever for curated Markdown reference documents."""

from __future__ import annotations

from collections import Counter
import math
import re
from pathlib import Path
from typing import Any

from hw_ai_support.query_terms import normalize_text, tokens


CHUNK_SIZE = 1800
_HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")
_SOURCE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


def _split_markdown(path: Path) -> list[dict[str, str]]:
	text = path.read_text(encoding="utf-8")
	sections: list[dict[str, str]] = []
	headings: list[str] = []
	body: list[str] = []

	def flush() -> None:
		content = "\n".join(body).strip()
		if not content:
			return
		full_heading = " > ".join(headings) or path.stem
		sources = _SOURCE.findall(content)
		source_name = "; ".join(dict.fromkeys(name for name, _ in sources)) or "Curated project guidance"
		source_url = "; ".join(dict.fromkeys(url for _, url in sources))
		content = _SOURCE.sub(lambda match: match.group(1), content)
		paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
		parts: list[str] = []
		current = ""
		for paragraph in paragraphs:
			if current and len(current) + len(paragraph) + 2 > CHUNK_SIZE:
				parts.append(current)
				current = ""
			if len(paragraph) > CHUNK_SIZE:
				for start in range(0, len(paragraph), CHUNK_SIZE):
					parts.append(paragraph[start:start + CHUNK_SIZE])
			elif current:
				current += "\n\n" + paragraph
			else:
				current = paragraph
		if current:
			parts.append(current)
		for part in parts:
			sections.append({
				"heading": full_heading,
				"source": source_name,
				"url": source_url,
				"text": f"{path.stem}\n{full_heading}\n{part}\nOfficial source: {source_name} {source_url}".strip(),
			})

	for line in text.splitlines():
		match = _HEADING.match(line)
		if match:
			flush()
			level = len(line) - len(line.lstrip("#"))
			headings = headings[:level - 1]
			headings.append(match.group(1).strip())
			body = []
		else:
			body.append(line)
	flush()
	return sections


def retrieve_markdown_chunks(question: str, expanded_terms: list[str], *, path: str | Path, limit: int = 6) -> list[dict[str, Any]]:
	"""Retrieve relevant passages from one curated Markdown reference file."""
	source = Path(path)
	if not source.is_file():
		return []
	chunks = _split_markdown(source)
	if not chunks:
		return []

	query_terms = list(dict.fromkeys(tokens(normalize_text(question) + " " + " ".join(expanded_terms))))
	query_counts = Counter(query_terms)
	if not query_counts:
		return []
	document_counts = [Counter(tokens(normalize_text(chunk["text"]))) for chunk in chunks]
	document_frequency: Counter[str] = Counter()
	for counts in document_counts:
		document_frequency.update(counts.keys())
	total = len(chunks)
	idf = {term: math.log(1 + total / (1 + count)) + 1 for term, count in document_frequency.items()}
	query_total = max(1, sum(query_counts.values()))
	query_vector = {term: (count / query_total) * idf.get(term, 0.0) for term, count in query_counts.items()}
	query_norm = math.sqrt(sum(value * value for value in query_vector.values()))
	if not query_norm:
		return []

	results = []
	for chunk, counts in zip(chunks, document_counts):
		length = max(1, sum(counts.values()))
		vector = {term: (count / length) * idf.get(term, 0.0) for term, count in counts.items()}
		norm = math.sqrt(sum(value * value for value in vector.values()))
		if not norm:
			continue
		score = sum(value * vector.get(term, 0.0) for term, value in query_vector.items()) / (query_norm * norm)
		if score > 0:
			results.append({**chunk, "score": round(score, 4), "page": 0})
	results.sort(key=lambda item: (-item["score"], item["heading"]))
	return results[:limit]
