"""Whitelisted, read-only chat endpoint."""

from __future__ import annotations

import json
import time

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from hw_ai_support import llm
from hw_ai_support.prompts import system_prompt
from hw_ai_support.retrieval import detect_language, retrieve_with_labels
from hw_ai_support.sanitizer import sanitize


def _friendly_error(language: str) -> str:
	return {
		"fr": "Le service d’assistance est temporairement indisponible. Réessayez dans un instant.",
		"ar": "خدمة المساعدة غير متاحة مؤقتاً. يرجى المحاولة مرة أخرى بعد قليل.",
	}.get(language, "The support service is temporarily unavailable. Please try again shortly.")


def _parse_history(history) -> list[dict[str, str]]:
	if isinstance(history, str):
		try:
			history = json.loads(history)
		except ValueError:
			raise frappe.ValidationError(_("Conversation history is invalid."))
	if history is None:
		return []
	if not isinstance(history, list):
		raise frappe.ValidationError(_("Conversation history is invalid."))
	clean = []
	for item in history[-10:]:
		if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"} or not isinstance(item.get("content"), str):
			raise frappe.ValidationError(_("Conversation history is invalid."))
		content = item["content"].strip()
		if not content or len(content) > 4000:
			raise frappe.ValidationError(_("Conversation history is invalid."))
		clean.append({"role": item["role"], "content": content})
	return clean


def _log(**values) -> None:
	try:
		frappe.get_doc({"doctype": "AI Interaction Log", **values}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="HW AI Support interaction logging error", message=frappe.get_traceback())


def _enforce_rate_limit() -> None:
	"""Use Frappe's limiter with the authenticated user as its cache identity."""
	frappe.form_dict["hw_ai_support_user"] = frappe.session.user
	rate_limit(key="hw_ai_support_user", limit=30, seconds=60, methods="POST", ip_based=False)(lambda: None)()


@frappe.whitelist(methods=["POST"])
def chat(message: str | None = None, history=None, language: str | None = None) -> dict:
	"""Answer using only permission-filtered Doctype metadata, never business data."""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please log in to use HW AI Support."))
	if not isinstance(message, str) or not message.strip():
		raise frappe.ValidationError(_("Please enter a question."))
	if len(message) > 2000:
		raise frappe.ValidationError(_("Your question must be 2,000 characters or fewer."))
	_enforce_rate_limit()
	history_items = _parse_history(history)
	started = time.monotonic()
	user = frappe.session.user
	response_language = language if language in {"en", "fr", "ar"} else detect_language(message)
	if any(term in message.lower() for term in ("stock", "inventory", "inventaire", "\u0645\u062e\u0632\u0648\u0646")):
		try:
			settings = frappe.get_single("HW AI Support Settings")
			enabled = bool(settings.tools_enabled and settings.business_data_mode != "Disabled")
		except Exception:
			enabled = False
		if enabled:
			from hw_ai_support.tools.data import get_stock_balance, search_items
			import re
			explicit = re.search(r"(?:item|article~'F7FA)\s+([A-Za-z0-9_.-]+)", message, re.IGNORECASE)
			code_match = explicit or re.search(r"\b[A-Z][A-Z0-9_.-]*_[A-Z0-9_-]+\b", message)
			item_code = code_match.group(1) if explicit else (code_match.group(0) if code_match else None)
			if not item_code:
				phrase_match = re.search(r"(?:item|article)\s+(.+?)(?:\\?|$)", message, re.IGNORECASE)
				query = phrase_match.group(1).strip() if phrase_match else ""
				candidates = search_items(query, user=user).get("candidates", []) if query else []
				if len(candidates) == 1:
					item_code = candidates[0].name
				elif candidates:
					labels = ", ".join(f"{row.name} ({row.item_name})" for row in candidates)
					reply = f"Please specify which item you mean: {labels}."
					return {"reply": reply, "language": response_language, "doctypes_used": ["Item"], "sources": ["Item search"]}
				else:
					reply = "Please include an item code, for example SKU_001."
					return {"reply": reply, "language": response_language, "doctypes_used": [], "sources": []}
			data = get_stock_balance(item_code=item_code, user=user)
			qty = data.get("total_quantity", 0)
			if response_language == "fr":
				reply = f"Le stock disponible pour {item_code} est de {qty} unites."
			elif response_language == "ar":
				reply = f"\\u0627\\u0644\\u0631\\u0635\\u064a\\u062f \\u0627\\u0644\\u0645\\u062a\\u0627\\u062d \\u0644\\u0644\\u0635\\u0646\\u0641 {item_code} \\u0647\\u0648 {qty} \\u0648\\u062d\\u062f\\u0629."
			else:
				reply = f"The available stock for {item_code} is {qty} units."
			_log(user=user, question=message.strip(), answer=reply, language=response_language, doctypes_used="Item, Bin", status="Success", sanitized=0, response_time_ms=int((time.monotonic() - started) * 1000))
			return {"reply": reply, "language": response_language, "doctypes_used": ["Item", "Bin"], "sources": ["Stock balance"]}

	try:
		result = retrieve_with_labels(message.strip(), user)
		response_language = result.normalized.language if result.normalized.language in {"en", "fr", "ar"} else "en"
		prompt = system_prompt(response_language, result.context, result.normalized.in_scope)
		reply = llm.ask(prompt, history_items + [{"role": "user", "content": message.strip()}])
		reply, was_sanitized = sanitize(reply, result.known_names, result.name_labels)
		status = "Success" if result.normalized.in_scope else "Blocked"
		_log(user=user, question=message.strip(), answer=reply, language=response_language, doctypes_used=", ".join(result.labels), status=status, sanitized=int(was_sanitized), response_time_ms=int((time.monotonic() - started) * 1000))
		return {"reply": reply, "language": response_language, "doctypes_used": result.labels}
	except frappe.ValidationError:
		raise
	except llm.LLMError as exc:
		frappe.log_error(title="HW AI Support chat provider error", message=str(exc))
		friendly = str(exc)
		_log(user=user, question=message.strip(), answer=friendly, language=response_language, doctypes_used="", status="Error", sanitized=0, error=friendly, response_time_ms=int((time.monotonic() - started) * 1000))
		return {"reply": friendly, "language": response_language, "error": True}
	except Exception:
		frappe.log_error(title="HW AI Support chat error", message=frappe.get_traceback())
		friendly = _friendly_error(response_language)
		_log(user=user, question=message.strip(), answer=friendly, language=response_language, doctypes_used="", status="Error", sanitized=0, error="Provider or server failure", response_time_ms=int((time.monotonic() - started) * 1000))
		return {"reply": friendly, "language": response_language, "error": True}







