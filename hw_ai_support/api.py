"""Permission-aware ERPNext help and read-only business insight endpoint."""

from __future__ import annotations

import json
import time

import frappe
from frappe import _
from frappe.exceptions import RateLimitExceededError
from frappe.rate_limiter import rate_limit

from hw_ai_support import llm
from hw_ai_support.prompts import business_answer_prompt, business_tool_prompt, system_prompt
from hw_ai_support.retrieval import detect_language, retrieve_with_labels
from hw_ai_support.sanitizer import sanitize
from hw_ai_support.query_terms import matched_concepts


def _friendly_error(language: str) -> str:
	return {"fr": "Le service d’assistance est temporairement indisponible. Réessayez dans un instant.", "ar": "خدمة المساعدة غير متاحة مؤقتاً. يرجى المحاولة مرة أخرى بعد قليل."}.get(language, "The support service is temporarily unavailable. Please try again shortly.")


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
		# History is client supplied. Ignore assistant-role entries so a caller
		# cannot smuggle fabricated model instructions into the conversation.
		if item["role"] == "user":
			clean.append({"role": "user", "content": content})
	return clean


def _relevant_history(history: list[dict[str, str]], message: str) -> list[dict[str, str]]:
	"""Keep history only when it is a clear follow-up or shares the current topic."""
	if not history:
		return []
	text = " ".join(message.casefold().split())
	follow_up_prefixes = (
		"and ", "also ", "what about ", "how about ", "why ", "tell me more", "explain that",
		"et ", "mais ", "et pour ", "et ça", "qu'en est-il", "و ماذا", "وماذا", "هل هذا", "ماذا عن",
	)
	if text.startswith(follow_up_prefixes):
		return history[-2:]
	current_topics = set(matched_concepts(message))
	if not current_topics:
		return []
	relevant = [item for item in history if current_topics.intersection(matched_concepts(item["content"]))]
	return relevant[-2:]


def _log(**values) -> None:
	try:
		settings = frappe.get_single("HW AI Support Settings")
		if not settings.store_question_text:
			values["question"] = _("Question not retained by privacy setting")
			values["answer"] = ""
		frappe.get_doc({"doctype": "AI Interaction Log", **values}).insert(ignore_permissions=True)
	except Exception:
		frappe.log_error(title="HW AI Support interaction logging error", message=frappe.get_traceback())


def _enforce_rate_limit() -> None:
	frappe.form_dict["hw_ai_support_user"] = frappe.session.user
	rate_limit(key="hw_ai_support_user", limit=30, seconds=60, methods="POST", ip_based=False)(lambda: None)()


def _within_daily_budget(user: str) -> bool:
	try:
		budget = max(1, int(frappe.get_single("HW AI Support Settings").daily_call_budget or 100))
		key = f"hw_ai_support:daily:{frappe.utils.today()}:{frappe.scrub(user)}"
		count = frappe.cache.incr(key)
		if count == 1:
			frappe.cache.expire(key, 86400)
		return count <= budget
	except Exception:
		# Cache failures should not turn a read-only support service into a bypass.
		frappe.log_error(title="HW AI Support budget check failed", message=frappe.get_traceback())
		return False


def _is_business_question(message: str) -> bool:
	text = message.casefold()
	terms = ("stock", "inventory", "quantity", "on hand", "in stock", "inventaire", "en stock", "profit", "profits", "revenue", "sales total", "sales last", "what were sales", "sales from", "sales between", "overdue", "unpaid", "outstanding invoice", "invoice due", "en retard", "facture impay", "factures en retard", "chiffre d’affaires", "bénéfice", "مخزون", "كمية", "ارباح", "المبيعات", "فواتير متأخرة", "فاتورة غير مدفوعة")
	return any(term in text for term in terms)


def _business_enabled() -> bool:
	try:
		settings = frappe.get_single("HW AI Support Settings")
		if not settings.tools_enabled or settings.business_data_mode == "Disabled":
			return False
		if settings.business_data_mode == "Local LLM only":
			return llm.provider_name() == "openai_compatible" and llm.is_local_endpoint()
		return bool(settings.business_data_mode == "Hosted LLM, aggregated results only" and settings.hosted_consent)
	except Exception:
		return False


def _business_chat(message: str, history: list[dict[str, str]], language: str, user: str) -> dict | None:
	from hw_ai_support.tools.executor import execute_tool
	from hw_ai_support.tools.registry import all_tools

	settings = frappe.get_single("HW AI Support Settings")
	tools = all_tools()
	started = time.monotonic()
	deadline = started + 45
	try:
		tool_prompt = business_tool_prompt(language) + f"\nCurrent site date: {frappe.utils.today()}. Resolve relative date expressions using this date."
		messages = history + [{"role": "user", "content": message}]
		tool_names, protected_values, results = [], [], []
		iterations = max(1, min(int(settings.max_tool_iterations or 2), 4))
		for _ in range(iterations):
			remaining = deadline - time.monotonic()
			if remaining <= 1:
				raise llm.LLMError("request_deadline")
			if settings.tool_calling_mode == "json_fallback":
				catalog = [{"name": tool.name, "description": tool.description, "parameters": tool.parameters} for tool in tools]
				text = llm.ask(tool_prompt + "\nSelect a tool only when needed. Return only JSON shaped as {\"tool_calls\":[{\"name\":string,\"arguments\":object}]}; return an empty array when no tool is needed. Available tools: " + json.dumps(catalog), messages, json_mode=True, timeout=remaining)
				payload = json.loads(text)
				calls = payload.get("tool_calls") if isinstance(payload, dict) else []
			else:
				_, calls = llm.ask_with_tools(tool_prompt, messages, [tool.schema() for tool in tools], timeout=remaining)
			if not isinstance(calls, list):
				calls = []
			if not calls:
				if not results:
					return None
				break
			round_results = []
			for call in calls[:5]:
				name = call.get("name") if isinstance(call, dict) else None
				result = execute_tool(name, call.get("arguments"), user=user)
				tool_names.append(name or "unknown")
				if result.get("status") != "ok":
					item = {"tool": name, "status": result.get("status"), "message": "No permitted result is available."}
				else:
					data = result.get("data") or {}
					# Hosted mode sends compact results, never invoice-level rows.
					if name == "get_overdue_invoices":
						data = {key: data.get(key) for key in ("complete", "count", "count_at_least", "totals_by_currency", "oldest_due_date", "message") if key in data}
					elif name == "get_stock_balance":
						data = {key: data.get(key) for key in ("found", "complete", "item_code", "stock_uom", "total_quantity", "message") if key in data}
					elif name == "search_items":
						data = {"candidates": data.get("candidates", [])[:5]}
						for candidate in data["candidates"]:
							if isinstance(candidate, dict):
								protected_values.extend(str(candidate.get(key)) for key in ("name", "item_name") if candidate.get(key))
					elif name in {"get_profit_summary", "get_report_data", "get_sales_summary"}:
						data = {key: data.get(key) for key in ("available", "complete", "count_at_least", "from_date", "to_date", "invoice_count", "total", "currency", "summary", "note", "message") if key in data}
					if name == "get_stock_balance":
						protected_values.extend(str(value) for value in (data.get("item_code"),) if value)
					item = {"tool": name, "status": "ok", "data": data}
				results.append(item)
				round_results.append(item)
			messages.append({"role": "user", "content": "Verified results from the read-only ERPNext tools: " + json.dumps(round_results, ensure_ascii=False, default=str)})
		remaining = deadline - time.monotonic()
		if remaining <= 1:
			raise llm.LLMError("request_deadline")
		answer = llm.ask(business_answer_prompt(language, message, json.dumps(results, ensure_ascii=False, default=str)), [{"role": "user", "content": "Summarize these verified ERPNext results."}], timeout=remaining)
		answer, was_sanitized = sanitize(answer, set(), {}, protected_values)
		labels = {"search_items": "Item search", "get_stock_balance": "Stock balance", "get_overdue_invoices": "Overdue invoices", "get_sales_summary": "Sales summary", "get_profit_summary": "Profit and Loss report", "get_report_data": "Profit and Loss report"}
		provider = llm.provider_name()
		model = (frappe.get_single("HW AI Support Settings").llm_model if provider == "openai_compatible" else frappe.conf.get("gemini_model")) or llm.DEFAULT_MODEL
		_log(user=user, question=message, answer=answer, language=language, doctypes_used=", ".join(labels.get(name, "ERPNext report") for name in tool_names), status="Success", sanitized=int(was_sanitized), response_time_ms=int((time.monotonic() - started) * 1000), intent="business_data", tool_calls_count=len(tool_names), provider=provider, model=model)
		return {"reply": answer, "language": language, "doctypes_used": list(labels.get(name, "ERPNext report") for name in tool_names), "sources": list(labels.get(name, "ERPNext report") for name in tool_names), "intent": "business_data"}
	except llm.LLMError:
		raise
	except Exception:
		frappe.log_error(title="HW AI Support business insight error", message=frappe.get_traceback())
		raise


@frappe.whitelist(methods=["POST"])
def chat(message: str | None = None, history=None, language: str | None = None) -> dict:
	if frappe.session.user == "Guest":
		raise frappe.PermissionError(_("Please log in to use HW AI Support."))
	if not isinstance(message, str) or not message.strip():
		raise frappe.ValidationError(_("Please enter a question."))
	if len(message) > 2000:
		raise frappe.ValidationError(_("Your question must be 2,000 characters or fewer."))
	started = time.monotonic()
	user = frappe.session.user
	response_language = detect_language(message)
	try:
		_enforce_rate_limit()
	except RateLimitExceededError:
		reply = _friendly_error(response_language)
		_log(user=user, question=message, answer=reply, language=response_language, doctypes_used="", status="Rate Limited", sanitized=0, error="Per-minute request limit", response_time_ms=int((time.monotonic() - started) * 1000), intent="unknown")
		return {"reply": reply, "language": response_language, "error": True}
	history_items = _relevant_history(_parse_history(history), message.strip())
	if not _within_daily_budget(user):
		reply = {"fr": "La limite quotidienne d’utilisation de l’assistance est atteinte. Réessayez demain.", "ar": "تم بلوغ حد الاستخدام اليومي للمساعدة. حاول مرة أخرى غداً."}.get(response_language, "The daily support usage limit has been reached. Please try again tomorrow.")
		_log(user=user, question=message, answer=reply, language=response_language, doctypes_used="", status="Rate Limited", sanitized=0, response_time_ms=int((time.monotonic() - started) * 1000), intent="unknown")
		return {"reply": reply, "language": response_language, "error": True}
	if _is_business_question(message):
		if not _business_enabled():
			reply = {"fr": "Les réponses sur les données de l’entreprise sont désactivées ou nécessitent le consentement de l’administrateur.", "ar": "الإجابات حول بيانات الشركة معطلة أو تتطلب موافقة المسؤول."}.get(response_language, "Business data answers are disabled or require administrator consent.")
			_log(user=user, question=message, answer=reply, language=response_language, doctypes_used="", status="Denied", sanitized=0, response_time_ms=int((time.monotonic() - started) * 1000), intent="business_data")
			return {"reply": reply, "language": response_language, "error": True}
		try:
			result = _business_chat(message.strip(), history_items, response_language, user)
			if result:
				return result
		except llm.LLMError:
			friendly = _friendly_error(response_language)
			_log(user=user, question=message, answer=friendly, language=response_language, doctypes_used="", status="Error", sanitized=0, error="LLM unavailable", response_time_ms=int((time.monotonic() - started) * 1000), intent="business_data")
			return {"reply": friendly, "language": response_language, "error": True}
		except Exception:
			frappe.log_error(title="HW AI Support business insight error", message=frappe.get_traceback())
			friendly = _friendly_error(response_language)
			_log(user=user, question=message, answer=friendly, language=response_language, doctypes_used="", status="Error", sanitized=0, error="Business insight failed", response_time_ms=int((time.monotonic() - started) * 1000), intent="business_data")
			return {"reply": friendly, "language": response_language, "error": True}

	try:
		result = retrieve_with_labels(message.strip(), user)
		response_language = result.normalized.language if result.normalized.language in {"en", "fr", "ar"} else response_language
		prompt = system_prompt(response_language, result.context, result.normalized.in_scope)
		reply = llm.ask(prompt, history_items + [{"role": "user", "content": message.strip()}])
		reply, was_sanitized = sanitize(reply, result.known_names, result.name_labels)
		status = "Success" if result.normalized.in_scope else "Blocked"
		provider = llm.provider_name()
		model = (frappe.get_single("HW AI Support Settings").llm_model if provider == "openai_compatible" else frappe.conf.get("gemini_model")) or llm.DEFAULT_MODEL
		_log(user=user, question=message.strip(), answer=reply, language=response_language, doctypes_used=", ".join(result.labels), status=status, sanitized=int(was_sanitized), response_time_ms=int((time.monotonic() - started) * 1000), intent="knowledge", provider=provider, model=model)
		return {"reply": reply, "language": response_language, "doctypes_used": result.labels, "sources": result.labels, "intent": "knowledge"}
	except frappe.ValidationError:
		raise
	except llm.LLMError:
		friendly = _friendly_error(response_language)
		_log(user=user, question=message.strip(), answer=friendly, language=response_language, doctypes_used="", status="Error", sanitized=0, error="LLM unavailable", response_time_ms=int((time.monotonic() - started) * 1000), intent="knowledge")
		return {"reply": friendly, "language": response_language, "error": True}
	except Exception:
		frappe.log_error(title="HW AI Support chat error", message=frappe.get_traceback())
		friendly = _friendly_error(response_language)
		_log(user=user, question=message.strip(), answer=friendly, language=response_language, doctypes_used="", status="Error", sanitized=0, error="Server failure", response_time_ms=int((time.monotonic() - started) * 1000), intent="knowledge")
		return {"reply": friendly, "language": response_language, "error": True}


@frappe.whitelist(methods=["POST"])
def ping_provider() -> dict:
	"""Administrator-only provider connectivity check; never exposes credentials."""
	if frappe.session.user == "Guest" or not frappe.has_permission("HW AI Support Settings", "write"):
		raise frappe.PermissionError(_("Only a System Manager can check provider settings."))
	return llm.ping()
