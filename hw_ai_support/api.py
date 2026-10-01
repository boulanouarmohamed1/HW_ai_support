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
	except Exception:
		frappe.log_error(title="HW AI Support chat error", message=frappe.get_traceback())
		friendly = _friendly_error(response_language)
		_log(user=user, question=message.strip(), answer=friendly, language=response_language, doctypes_used="", status="Error", sanitized=0, error="Provider or server failure", response_time_ms=int((time.monotonic() - started) * 1000))
		return {"reply": friendly, "language": response_language, "error": True}
