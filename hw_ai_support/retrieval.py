"""Language classification and lightweight metadata retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import frappe

from hw_ai_support.knowledge import DoctypeKnowledge, build_doctype_doc, get_accessible_doctypes
from hw_ai_support.pdf_retrieval import retrieve_pdf_context
from hw_ai_support.query_terms import CONCEPTS, expand_terms, hinted_doctypes, matched_concepts, normalize_text, tokens

OUT_OF_SCOPE = ("poem", "capital of", "write code", "politic", "weather", "recette", "poème", "météo", "عاصمة", "قصيدة", "طقس")


@dataclass
class NormalizedQuery:
	language: str
	in_scope: bool
	keywords: list[str]
	likely_doctypes: list[str]
	concepts: list[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
	normalized: NormalizedQuery
	documents: list[DoctypeKnowledge]
	labels: list[str]
	known_names: set[str]
	name_labels: dict[str, str]
	pdf_context: str = ""

	@property
	def context(self) -> str:
		parts = [str(document) for document in self.documents]
		if self.pdf_context:
			parts.append(self.pdf_context)
		return "\n\n".join(parts)


def detect_language(text: str) -> str:
	if re.search(r"[\u0600-\u06ff]", text):
		return "ar"
	# Accent and common word checks make fallback useful without a language SDK.
	if re.search(r"[àâçéèêëîïôùûüÿœ]", text.lower()) or re.search(r"\b(comment|où|pourquoi|facture|commande|bonjour|quelle|quelles|combien|fournisseur|retard|congé|bénéfice)\b", text.lower()):
		return "fr"
	return "en"


def _fallback(question: str) -> NormalizedQuery:
	normalized = normalize_text(question)
	out_of_scope = any(normalize_text(term) in normalized for term in OUT_OF_SCOPE)
	return NormalizedQuery(
		detect_language(question),
		not out_of_scope,
		expand_terms(question),
		hinted_doctypes(question),
		matched_concepts(question),
	)


def normalize_query(question: str) -> NormalizedQuery:
	"""Normalize locally to avoid an extra provider round-trip per question."""
	return _fallback(question)


def _phrase_in(phrase: str, text: str) -> bool:
	phrase = normalize_text(phrase)
	return bool(phrase and f" {phrase} " in f" {text} ")


def _score(entry: dict, normalized: NormalizedQuery) -> int:
	# Internal names are used only locally for matching and are never sent to the LLM.
	name = normalize_text(str(entry.get("name", "")))
	label = normalize_text(str(entry.get("label", "")))
	description = normalize_text(str(entry.get("description", "")))
	module = normalize_text(str(entry.get("module", "")))
	haystack = set(tokens(name + " " + label + " " + module + " " + description))
	label_texts = [name, label]
	for lang in ("en", "fr", "ar"):
		translated = normalize_text(frappe._(entry.get("label", ""), lang=lang))
		label_texts.append(translated)
		haystack.update(tokens(translated))
	words = set(normalized.keywords)
	score = sum(1 for token in words if token in haystack)
	if name in {normalize_text(value) for value in normalized.likely_doctypes}:
		score += 16
	for concept in normalized.concepts:
		definition = CONCEPTS[concept]
		if any(_phrase_in(phrase, text) for phrase in definition["phrases"] for text in label_texts):
			score += 8
		elif entry.get("name") in definition["doctypes"]:
			score += 7
	return score


def retrieve(question: str, user: str) -> RetrievalResult:
	normalized = normalize_query(question)
	if not normalized.in_scope:
		return RetrievalResult(normalized, [], [], set(), {})
	scored = [(entry, _score(entry, normalized)) for entry in get_accessible_doctypes(user)]
	selected = [entry for entry, score in sorted(scored, key=lambda item: (-item[1], item[0]["name"])) if score > 0][:5]
	documents: list[DoctypeKnowledge] = []
	for entry in selected:
		try:
			documents.append(build_doctype_doc(entry["name"], user, normalized.language if normalized.language != "other" else "en"))
		except Exception:
			frappe.log_error(title="HW AI Support metadata error", message=frappe.get_traceback())
	known_names: set[str] = set()
	name_labels: dict[str, str] = {}
	for document in documents:
		known_names.update(document.known_internal_names)
		name_labels.update(document.internal_name_labels)
	pdf_context = retrieve_pdf_context(question, normalized.keywords)
	return RetrievalResult(normalized, documents, [document.doctype_label for document in documents], known_names, name_labels, pdf_context)


def retrieve_with_labels(question: str, user: str) -> RetrievalResult:
	"""Compatibility wrapper with stable selected-document labels."""
	return retrieve(question, user)
