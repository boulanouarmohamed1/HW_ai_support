"""Small provider boundary for hosted LLM calls.

Only this module knows about Gemini.  Keep application policy in prompts.py
and API validation in api.py so this file can be replaced by another backend.
"""

from __future__ import annotations

import os
import time
from typing import Any

import frappe
import requests


class LLMError(Exception):
	"""Safe exception raised to the application layer for provider failures."""


DEFAULT_MODEL = "gemini-2.5-flash"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _key() -> str | None:
	return frappe.conf.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")


def _provider_error(message: str, exc: Exception | None = None) -> LLMError:
	frappe.log_error(title="HW AI Support Gemini error", message=message if exc is None else f"{message}: {exc!r}")
	if "403" in message or "permission_denied" in message.lower():
		return LLMError("The support service is temporarily unavailable.")
	return LLMError("The AI service is unavailable.")


def ask(system_prompt: str, messages: list[dict[str, str]], json_mode: bool = False) -> str:
	"""Return Gemini's text response without exposing configuration or provider errors."""
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
		"generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
	}
	if json_mode:
		payload["generationConfig"]["responseMimeType"] = "application/json"

	for attempt in range(3):
		try:
			response = requests.post(
				ENDPOINT.format(model=model), headers={"x-goog-api-key": key, "Content-Type": "application/json"}, json=payload, timeout=60
			)
			if response.status_code == 429 or response.status_code >= 500:
				if attempt < 2:
					time.sleep(2**attempt)
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
			if attempt < 2:
				time.sleep(2**attempt)
				continue
			raise _provider_error("Gemini network failure", exc)
		except (ValueError, requests.RequestException) as exc:
			raise _provider_error("Gemini response failure", exc)

	raise _provider_error("Gemini retry attempts exhausted")

