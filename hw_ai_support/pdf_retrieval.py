"""Retrieve relevant passages from the bundled ERPNext documentation PDF."""

from __future__ import annotations

from pathlib import Path
import re

import frappe

from hw_ai_support.pdf_vector_store import retrieve_pdf_chunks
from hw_ai_support.markdown_vector_store import retrieve_markdown_chunks
from hw_ai_support.query_terms import CONCEPTS, STOP_WORDS, expand_terms, matched_concepts, normalize_text, tokens

PDF_PATH = Path(__file__).resolve().parent / "resources" / "ERPNext_Documentation_and_Use_Cases.pdf"
MARKDOWN_PATH = Path(__file__).resolve().parent / "resources" / "ERPNext_Phase2_Knowledge.md"
_ALL_STOP_WORDS = set().union(*STOP_WORDS.values())


def _rerank(question: str, candidates: list[dict], expanded_terms: list[str]) -> list[dict]:
	"""Boost passages with question coverage and procedural detail; demote TOCs."""
	core_terms = set(tokens(question)) - _ALL_STOP_WORDS
	concepts = matched_concepts(question)
	how_to = bool(re.search(r"\b(how|create|make|where|find|comment|creer|creer|ouvrir|faire|كيف|أين|اين|أنشئ|انشئ)\b", normalize_text(question)))
	expanded = set(expanded_terms) - _ALL_STOP_WORDS
	ranked = []
	for hit in candidates:
		text = hit.get("text", "")
		normalized_text = normalize_text(text)
		passage_terms = set(tokens(text))
		coverage = len(core_terms & passage_terms) / max(1, len(core_terms))
		expanded_coverage = len(expanded & passage_terms) / max(1, len(expanded))
		concept_match = any(
			(normalize_text(alias).count(" ") > 0 or concept in {"quotation", "stock", "profit"})
			and normalize_text(alias)
			and f" {normalize_text(alias)} " in f" {normalized_text} "
			for concept in concepts
			for alias in CONCEPTS[concept]["phrases"]
		)
		procedural = how_to and (
			" steps " in f" {normalized_text} "
			or " prerequisites " in f" {normalized_text} "
			or bool(re.search(r"\b[1-9][.)]\s", text))
		)
		score = float(hit.get("score", 0)) * 0.5 + coverage * 0.40 + expanded_coverage * 0.10
		if concept_match:
			score += 0.06
		if procedural:
			score += 0.18
		if how_to and re.search(r"\bopen\b.{0,50}\bquotation\b.{0,30}\badd\b", normalized_text):
			score += 0.16
		if "table of contents" in normalized_text:
			score -= 0.65
		if re.search(r"(?:\.\s*){6,}", text):
			score -= 0.30
		ranked_hit = dict(hit)
		ranked_hit["_retrieval_score"] = round(score, 4)
		ranked.append((score, ranked_hit))
	ranked.sort(key=lambda item: (-item[0], -float(item[1].get("score", 0)), int(item[1].get("page", 0))))
	return [hit for _, hit in ranked[:5]]


def retrieve_pdf_context(question: str, keywords: list[str] | None = None) -> str:
	"""Retrieve and rank grounded passages from the PDF and curated Markdown guide."""
	query_terms = keywords or expand_terms(question)
	query = " ".join(dict.fromkeys(query_terms))
	hits = []
	if PDF_PATH.is_file():
		index_path = Path(frappe.get_site_path("private", "files", "hw_ai_support_erpnext_docs.sqlite3"))
		try:
			hits.extend(retrieve_pdf_chunks(query, pdf_path=PDF_PATH, db_path=index_path, limit=30))
		except Exception:
			frappe.log_error(title="HW AI Support PDF retrieval error", message=frappe.get_traceback())
	try:
		hits.extend(retrieve_markdown_chunks(question, query_terms, path=MARKDOWN_PATH, limit=12))
	except Exception:
		frappe.log_error(title="HW AI Support Markdown retrieval error", message=frappe.get_traceback())
	if not hits:
		return ""
	hits = [
		hit for hit in _rerank(question, hits, query_terms)
		if hit.get("_retrieval_score", 0) >= (0.26 if hit.get("heading") else 0.30)
	]
	passages = []
	for hit in hits:
		if hit.get("heading"):
			source = f"; official reference: {hit['url']}" if hit.get("url") else ""
			passages.append(f"Curated ERPNext reference, {hit['heading']} (source: {hit['source']}{source}):\n{hit['text']}")
		else:
			passages.append(f"ERPNext documentation PDF, page {hit['page']}:\n{hit['text']}")
	return "\n\n".join(passages)
