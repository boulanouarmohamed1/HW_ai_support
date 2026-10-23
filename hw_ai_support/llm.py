"""Provider boundary for hosted Gemini and OpenAI-compatible local models.

Keep provider-specific request and credential handling here. Application policy
belongs in prompts.py and request validation in api.py.
"""

from __future__ import annotations

import os
import json
import time
from typing import Any

import frappe
import requests


class LLMError(Exception):
	"""Safe exception raised to the application layer for provider failures."""


DEFAULT_MODEL = "gemini-2.5-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
REQUEST_TIMEOUT = 20


def _key() -> str | None:
	return frappe.conf.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")


def provider_name() -> str:
	try:
		return frappe.get_single("HW AI Support Settings").llm_provider or "gemini"
	except Exception:
		return "gemini"


def is_local_endpoint() -> bool:
	try:
		from urllib.parse import urlparse
		url = frappe.get_single("HW AI Support Settings").llm_base_url or ""
		host = (urlparse(url).hostname or "").lower()
		return host in {"localhost", "127.0.0.1", "::1"}
	except Exception:
		return False


def _openai_config():
	settings = frappe.get_single("HW AI Support Settings")
	base = (settings.llm_base_url or frappe.conf.get("hw_ai_openai_base_url") or "").rstrip("/")
	model = settings.llm_model or frappe.conf.get("hw_ai_openai_model") or ""
	key = frappe.conf.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
	if not base or not model or (not key and not is_local_endpoint()):
		raise LLMError("provider_unavailable")
	if not base.endswith("/v1"):
		base += "/v1"
	return base + "/chat/completions", model, key


def _openai_messages(system: str, messages: list[dict[str, str]]) -> list[dict[str, str]]:
	return [{"role": "system", "content": system}] + [{"role": "assistant" if item.get("role") == "assistant" else "user", "content": item.get("content", "")} for item in messages]


def _ask_openai(system: str, messages: list[dict[str, str]], tools: list[dict] | None = None, json_mode: bool = False, timeout: float = REQUEST_TIMEOUT) -> tuple[str, list[dict]]:
	url, model, key = _openai_config()
	payload: dict[str, Any] = {"model": model, "messages": _openai_messages(system, messages), "temperature": 0.1, "max_tokens": int(frappe.conf.get("hw_ai_max_output_tokens", 1024))}
	if tools:
		payload["tools"] = tools
		payload["tool_choice"] = "auto"
	if json_mode:
		payload["response_format"] = {"type": "json_object"}
	headers = {"Content-Type": "application/json"}
	if key:
		headers["Authorization"] = f"Bearer {key}"
	try:
		response = requests.post(url, headers=headers, json=payload, timeout=min(REQUEST_TIMEOUT, max(1, timeout)))
		if response.status_code >= 400:
			raise _provider_error(f"OpenAI-compatible HTTP {response.status_code}")
		choice = (response.json().get("choices") or [])[0]["message"]
		calls = []
		for call in choice.get("tool_calls") or []:
			function = call.get("function") or {}
			try:
				arguments = json.loads(function.get("arguments") or "{}")
			except ValueError:
				arguments = None
			calls.append({"name": function.get("name"), "arguments": arguments})
		return choice.get("content") or "", calls
	except LLMError:
		raise
	except (requests.RequestException, ValueError, KeyError, IndexError) as exc:
		raise _provider_error("OpenAI-compatible request failed", exc)


def _provider_error(message: str, exc: Exception | None = None) -> LLMError:
	frappe.log_error(title="HW AI Support provider error", message=message if exc is None else f"{message}: {exc!r}")
	if "403" in message or "permission_denied" in message.lower():
		return LLMError("The support service is temporarily unavailable.")
	return LLMError("The AI service is unavailable.")


def ask(system_prompt: str, messages: list[dict[str, str]], json_mode: bool = False, timeout: float = REQUEST_TIMEOUT) -> str:
	"""Return provider text without exposing credentials or diagnostics to users."""
	if provider_name() == "openai_compatible":
		text, _ = _ask_openai(system_prompt, messages, json_mode=json_mode, timeout=timeout)
		if not text.strip():
			raise _provider_error("OpenAI-compatible empty response")
		return text.strip()
	key = _key()
	if not key:
		raise LLMError("The support service is temporarily unavailable.")

	model = frappe.conf.get("gemini_model") or DEFAULT_MODEL
	payload: dict[str, Any] = {
		"contents": [
			{"role": "model" if item.get("role") == "assistant" else "user", "parts": [{"text": item.get("content", "")}]} 
			for item in messages
		],
		"systemInstruction": {"parts": [{"text": system_prompt}]},
		"generationConfig": {"temperature": 0.2, "maxOutputTokens": int(frappe.conf.get("hw_ai_max_output_tokens", 1024))},
	}
	if json_mode:
		payload["generationConfig"]["responseMimeType"] = "application/json"

	for attempt in range(2):
		try:
			response = requests.post(
				ENDPOINT.format(model=model), headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=payload, timeout=min(REQUEST_TIMEOUT, max(1, timeout))
			)
			if response.status_code == 429 or response.status_code >= 500:
				if attempt < 1:
					time.sleep(0.5)
					continue
				raise _provider_error(f"Gemini HTTP {response.status_code}")
			if response.status_code >= 400:
				raise _provider_error(f"Gemini HTTP {response.status_code}")
			data = response.json()
			candidates = data.get("candidates") or []
			if not candidates:
				reason = data.get("promptFeedback") or "No candidates"
				raise _provider_error(f"Gemini empty/blocked response: {reason}")
			candidate = candidates[0]
			text = "".join(part.get("text", "") for part in (candidate.get("content") or {}).get("parts", []))
			if not text.strip():
				raise _provider_error(f"Gemini empty/blocked response: {candidate.get('finishReason', 'unknown')}")
			return text.strip()
		except LLMError:
			raise
		except (requests.Timeout, requests.ConnectionError) as exc:
			if attempt < 1:
				time.sleep(0.5)
				continue
			raise _provider_error("Gemini network failure", exc)
		except (ValueError, requests.RequestException) as exc:
			raise _provider_error("Gemini response failure", exc)

	raise _provider_error("Gemini retry attempts exhausted")


def ask_with_tools(system_prompt: str, messages: list[dict[str, str]], tools: list[dict], timeout: float = REQUEST_TIMEOUT) -> tuple[str, list[dict]]:
	"""Ask Gemini for a concise answer or validated function calls.

	The model receives tool schemas only; business records are fetched by the
	server after validating each requested call.
	"""
	if provider_name() == "openai_compatible":
		return _ask_openai(system_prompt, messages, tools, timeout=timeout)
	key = _key()
	if not key:
		raise LLMError("provider_unavailable")
	model = frappe.conf.get("gemini_model") or DEFAULT_MODEL
	payload: dict[str, Any] = {
		"contents": [{"role": "model" if item.get("role") == "assistant" else "user", "parts": [{"text": item.get("content", "")}]} for item in messages],
		"systemInstruction": {"parts": [{"text": system_prompt}]},
		"tools": [{"functionDeclarations": [{"name": tool["function"]["name"], "description": tool["function"]["description"], "parameters": tool["function"]["parameters"]} for tool in tools]}],
		"toolConfig": {"functionCallingConfig": {"mode": "AUTO"}},
		"generationConfig": {"temperature": 0.1, "maxOutputTokens": int(frappe.conf.get("hw_ai_max_output_tokens", 1024))},
	}
	try:
		response = requests.post(ENDPOINT.format(model=model), headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=payload, timeout=min(REQUEST_TIMEOUT, max(1, timeout)))
		if response.status_code >= 400:
			raise _provider_error(f"Gemini HTTP {response.status_code}")
		candidates = response.json().get("candidates") or []
		if not candidates:
			raise _provider_error("Gemini empty/blocked response")
		parts = (candidates[0].get("content") or {}).get("parts", [])
		calls = []
		text_parts = []
		for part in parts:
			if isinstance(part.get("functionCall"), dict):
				call = part["functionCall"]
				calls.append({"name": call.get("name"), "arguments": call.get("args") or {}})
			elif isinstance(part.get("text"), str):
				text_parts.append(part["text"])
		return "\n".join(text_parts).strip(), calls
	except LLMError:
		raise
	except (requests.RequestException, ValueError, KeyError) as exc:
		raise _provider_error("Gemini tool-call request failed", exc)


def ping() -> dict:
	"""Verify the configured provider without returning secrets or raw HTTP details."""
	provider = provider_name()
	try:
		answer = ask("Reply with only OK.", [{"role": "user", "content": "OK"}])
		return {"ok": bool(answer), "provider": provider, "model": (frappe.get_single("HW AI Support Settings").llm_model if provider == "openai_compatible" else frappe.conf.get("gemini_model")) or DEFAULT_MODEL}
	except LLMError:
		return {"ok": False, "provider": provider, "model": (frappe.get_single("HW AI Support Settings").llm_model if provider == "openai_compatible" else frappe.conf.get("gemini_model")) or DEFAULT_MODEL, "diagnostic": "Check provider settings and the server Error Log."}

