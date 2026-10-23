"""Language-aware lexical normalization and ERPNext query expansion."""

from __future__ import annotations

import re
import unicodedata


STOP_WORDS = {
	"en": set("a an the and or but what which who where when why how do does did can could should would i me my we our you your is are was were be been being to of for from in on at by with about tell show find get give please this that it its have has had still".split()),
	"fr": set("a au aux avec ce ces cette comment dans de des du elle en est et la le les leur ma mes moi mon ne notre nous où par pas pour qu que quelle quelles quel qui sa se son sur un une vos votre vous".split()),
	"ar": set("ما ماذا كيف هل اين أين متى لماذا من عن على في الى إلى هو هي هذا هذه ذلك تلك و او أو من فضلك لي منى".split()),
}


# Each concept contains natural phrases in all supported languages plus likely
# DocTypes. These names are used only for local retrieval, never as answer text.
CONCEPTS: dict[str, dict[str, tuple[str, ...]]] = {
	"quotation": {
		"phrases": ("quotation", "sales quotation", "quote", "sales quote", "estimate", "devis", "offre de prix", "عرض سعر", "عرض أسعار", "عرض اسعار"),
		"doctypes": ("Quotation",),
	},
	"sales order": {
		"phrases": ("sales order", "customer order", "order from customer", "commande client", "commande de vente", "أمر مبيعات", "امر مبيعات", "طلب مبيعات"),
		"doctypes": ("Sales Order",),
	},
	"purchase order": {
		"phrases": ("purchase order", "supplier order", "vendor order", "commande fournisseur", "أمر شراء", "امر شراء", "طلب شراء"),
		"doctypes": ("Purchase Order",),
	},
	"sales invoice": {
		"phrases": ("sales invoice", "customer invoice", "invoice to customer", "facture client", "facture de vente", "فاتورة مبيعات", "فاتورة العميل"),
		"doctypes": ("Sales Invoice",),
	},
	"purchase invoice": {
		"phrases": ("purchase invoice", "supplier invoice", "vendor invoice", "supplier bill", "facture fournisseur", "facture d'achat", "فاتورة شراء", "فاتورة المورد"),
		"doctypes": ("Purchase Invoice",),
	},
	"invoice": {
		"phrases": ("invoice", "bill", "facture", "فاتورة"),
		"doctypes": ("Sales Invoice", "Purchase Invoice"),
	},
	"payment": {
		"phrases": ("payment entry", "pay a supplier", "pay supplier", "supplier payment", "customer payment", "payment to supplier", "paiement fournisseur", "payer le fournisseur", "règlement fournisseur", "دفع للمورد", "سداد المورد", "سداد فاتورة"),
		"doctypes": ("Payment Entry",),
	},
	"chart of accounts": {
		"phrases": ("chart of accounts", "account", "open account", "open an account", "create account", "create an account", "new account", "ledger account", "plan comptable", "compte comptable", "créer un compte", "ouvrir un compte", "دليل الحسابات", "حساب", "فتح حساب", "إنشاء حساب"),
		"doctypes": ("Account",),
	},
	"bank account": {
		"phrases": ("bank account", "company bank account", "compte bancaire", "compte de banque", "حساب بنكي", "حساب مصرفي"),
		"doctypes": ("Bank Account",),
	},
	"stock": {
		"phrases": ("stock", "inventory", "on hand", "available quantity", "stock balance", "inventaire", "quantité en stock", "quantite en stock", "niveau de stock", "مخزون", "كمية المخزون", "كمية الصنف"),
		"doctypes": ("Item", "Bin", "Warehouse"),
	},
	"sales": {
		"phrases": ("sales", "revenue", "turnover", "sales total", "chiffre d'affaires", "chiffre d’affaires", "ventes", "المبيعات", "إيرادات"),
		"doctypes": ("Sales Invoice",),
	},
	"profit": {
		"phrases": ("profit", "net profit", "profit and loss", "profit loss", "profit and loss statement", "income statement", "benefit", "bénéfice", "benefice", "résultat net", "compte de résultat", "compte de resultat", "état des résultats", "etat des resultats", "الربح", "صافي الربح"),
		"doctypes": (),
	},
	"purchase receipt": {
		"phrases": ("purchase receipt", "goods receipt", "received goods", "reception de marchandises", "réception de marchandises", "استلام البضاعة", "استلام المشتريات"),
		"doctypes": ("Purchase Receipt",),
	},
	"delivery note": {
		"phrases": ("delivery note", "delivery", "shipment", "bon de livraison", "livraison", "إشعار تسليم", "مذكرة تسليم"),
		"doctypes": ("Delivery Note",),
	},
	"employee leave": {
		"phrases": ("leave application", "leave request", "request leave", "employee leave", "vacation days", "vacation request", "leave balance", "leave approver", "leave approval", "approve leave request", "manager approves leave", "demande de congé", "approbation des congés", "approbateur de congé", "solde de congés", "jours de vacances", "طلب إجازة", "رصيد الإجازات", "أيام الإجازة", "موافقة الإجازة", "مسؤول الموافقة على الإجازة"),
		"doctypes": ("Leave Application", "Leave Allocation", "Leave Type", "Employee", "Department", "Workflow"),
	},
	"salary": {
		"phrases": ("salary structure", "salary slip", "employee salary", "payroll", "salaire", "fiche de paie", "مسير الرواتب", "راتب الموظف"),
		"doctypes": ("Salary Structure", "Salary Slip", "Employee"),
	},
	"attendance": {
		"phrases": ("employee attendance", "who was absent", "employee absence", "absent yesterday", "attendance", "absence", "présence", "absent hier", "غياب الموظف", "من تغيب", "الحضور"),
		"doctypes": ("Attendance", "Employee"),
	},
}

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_ARABIC_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_UNSTEMMED_S = {"business", "news", "status", "analysis", "devis", "frais", "temps", "mois", "pays", "mais", "corps", "cours"}
_FRENCH_MARKERS = ("comment", "pourquoi", "facture", "factures", "devis", "quelle", "quelles", "combien", "fournisseur", "retard", "conge", "benefice", "compte")


def normalize_text(text: str) -> str:
	"""Normalize accents, punctuation, underscores, and common Arabic variants."""
	value = unicodedata.normalize("NFKC", text or "").casefold().replace("_", " ")
	value = _ARABIC_DIACRITICS.sub("", value)
	value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي"}))
	value = unicodedata.normalize("NFD", value)
	value = "".join(char for char in value if unicodedata.category(char) != "Mn")
	return " ".join(_TOKEN_RE.findall(value))


def tokens(text: str) -> list[str]:
	result = []
	for token in _TOKEN_RE.findall(normalize_text(text)):
		if re.search(r"[\u0600-\u06FF]", token):
			result.append(token)
		elif token.endswith("ies") and len(token) > 5:
			result.append(token[:-3] + "y")
		elif token.endswith("s") and len(token) > 4 and token not in _UNSTEMMED_S:
			result.append(token[:-1])
		else:
			result.append(token)
	return result


def matched_concepts(text: str) -> list[str]:
	query_tokens = tokens(text)
	matched: dict[str, tuple[str, ...]] = {}
	for concept, definition in CONCEPTS.items():
		phrases = [tuple(tokens(phrase)) for phrase in definition["phrases"]]
		found = [phrase for phrase in phrases if _contains_sequence(query_tokens, phrase)]
		if found:
			matched[concept] = max(found, key=len)
	# Prefer a specific phrase over a generic word contained inside it, e.g.
	# "sales order" over "sales" or "supplier invoice" over "invoice".
	return [
		concept
		for concept, phrase in matched.items()
		if not any(
			other_phrase != phrase and len(other_phrase) > len(phrase) and _contains_sequence(other_phrase, phrase)
			for other_phrase in matched.values()
		)
	]


def _contains_sequence(haystack: list[str] | tuple[str, ...], needle: tuple[str, ...]) -> bool:
	return bool(needle) and any(tuple(haystack[index:index + len(needle)]) == needle for index in range(len(haystack) - len(needle) + 1))


def expand_terms(text: str, *, limit: int = 32) -> list[str]:
	"""Return useful original and cross-language terms for lexical RAG."""
	normalized = normalize_text(text)
	language = "ar" if re.search(r"[\u0600-\u06FF]", text or "") else "fr" if any(ch in "àâçéèêëîïôùûüÿœ" for ch in (text or "").casefold()) or any(f" {marker} " in f" {normalized} " for marker in _FRENCH_MARKERS) else "en"
	terms: list[str] = []
	seen: set[str] = set()
	for token in tokens(text):
		if token in STOP_WORDS[language] or len(token) < 2 or token in seen:
			continue
		seen.add(token)
		terms.append(token)
	for concept in matched_concepts(text):
		definition = CONCEPTS[concept]
		for phrase in (concept, *definition["phrases"]):
			for token in tokens(phrase):
				if token not in STOP_WORDS[language] and token not in seen:
					seen.add(token)
					terms.append(token)
					if len(terms) >= limit:
						return terms
	return terms[:limit]


def hinted_doctypes(text: str) -> list[str]:
	seen: set[str] = set()
	result: list[str] = []
	for concept in matched_concepts(text):
		for doctype in CONCEPTS[concept]["doctypes"]:
			if doctype not in seen:
				seen.add(doctype)
				result.append(doctype)
	return result
