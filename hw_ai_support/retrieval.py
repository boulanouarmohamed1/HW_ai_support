"""Language classification and lightweight metadata retrieval."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

import frappe

from hw_ai_support import llm
from hw_ai_support.knowledge import DoctypeKnowledge, build_doctype_doc, get_accessible_doctypes
from hw_ai_support.prompts import NORMALIZE_SYSTEM_PROMPT, normalization_messages

SYNONYMS = {
	"invoice": {"invoice", "facture", "فاتورة"},
	"quotation": {"quotation", "quote", "devis", "عرض سعر", "عرض"},
	"order": {"order", "commande", "طلب"},
	"delivery": {"delivery", "livraison", "تسليم"},
	"stock": {"stock", "inventory", "inventaire", "مخزون"},
	"customer": {"customer", "client", "عميل"},
	"supplier": {"supplier", "fournisseur", "مورد"},
	"payment": {"payment", "paiement", "دفع"},
	"credit note": {"credit note", "avoir", "إشعار دائن"},
}
OUT_OF_SCOPE = ("poem", "capital of", "write code", "politic", "weather", "recette", "poème", "météo", "عاصمة", "قصيدة", "طقس")


@dataclass
class NormalizedQuery:
	language: str
	in_scope: bool
	keywords: list[str]
	likely_doctypes: list[str]


@dataclass
class RetrievalResult:
	normalized: NormalizedQuery
	documents: list[DoctypeKnowledge]
	labels: list[str]
	known_names: set[str]
	name_labels: dict[str, str]

	@property
	def context(self) -> str:
		return "\n\n".join(str(document) for document in self.documents)


def detect_language(text: str) -> str:
	if re.search(r"[\u0600-\u06ff]", text):
		return "ar"
	# Accent and common word checks make fallback useful without a language SDK.
	if re.search(r"[àâçéèêëîïôùûüÿœ]", text.lower()) or re.search(r"\b(comment|où|pourquoi|facture|commande|bonjour)\b", text.lower()):
		return "fr"
	return "en"


def _fallback(question: str) -> NormalizedQuery:
	words = re.findall(r"[\wÀ-ÿ\u0600-\u06ff]+", question.lower())
	return NormalizedQuery(detect_language(question), not any(term in question.lower() for term in OUT_OF_SCOPE), words[:12], [])


def normalize_query(question: str) -> NormalizedQuery:
	try:
		payload = json.loads(llm.ask(NORMALIZE_SYSTEM_PROMPT, normalization_messages(question), json_mode=True))
		language = payload.get("language") if payload.get("language") in {"en", "fr", "ar", "other"} else detect_language(question)
		return NormalizedQuery(
			language, bool(payload.get("in_scope")),
			[str(item)[:80] for item in payload.get("english_keywords", []) if isinstance(item, str)][:12],
			[str(item)[:100] for item in payload.get("likely_doctypes", []) if isinstance(item, str)][:8],
		)
	except Exception:
		return _fallback(question)


def _tokens(value: str) -> set[str]:
	return {item.lower() for item in re.findall(r"[\wÀ-ÿ\u0600-\u06ff]+", value or "") if len(item) > 1}


def _score(entry: dict, normalized: NormalizedQuery) -> int:
	# Internal names are used only locally for matching and are never sent to the LLM.
	haystack = _tokens(" ".join(str(entry.get(key, "")) for key in ("name", "label", "module", "description")))
	for lang in ("en", "fr", "ar"):
		haystack.update(_tokens(frappe._(entry["label"], lang=lang)))
	words = set(normalized.keywords) | set(_tokens(" ".join(normalized.likely_doctypes)))
	for canonical, variants in SYNONYMS.items():
		if words & variants:
			words.update(variants)
	return sum(4 if token in _tokens(" ".join(normalized.likely_doctypes)) else 1 for token in words if token in haystack)


def retrieve(question: str, user: str) -> RetrievalResult:
	normalized = normalize_query(question)
	if not normalized.in_scope:
		return RetrievalResult(normalized, [], [], set(), {})
	scored = [(entry, _score(entry, normalized)) for entry in get_accessible_doctypes(user)]
	selected = [entry for entry, score in sorted(scored, key=lambda item: item[1], reverse=True) if score > 0][:5]
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
	return RetrievalResult(normalized, documents, [document.doctype_label for document in documents], known_names, name_labels)


def retrieve_with_labels(question: str, user: str) -> RetrievalResult:
	"""Compatibility wrapper with stable selected-document labels."""
	return retrieve(question, user)
