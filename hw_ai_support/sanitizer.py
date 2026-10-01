"""Last defence against accidentally displayed internal metadata names."""

from __future__ import annotations

import re


def sanitize(answer: str, known_names: set[str], labels: dict[str, str] | None = None) -> tuple[str, bool]:
	labels = labels or {}
	clean = re.sub(r"```[\s\S]*?```", "", answer).strip()
	# Gemini sometimes uses Markdown hard-break escapes; they are not useful in
	# the chat bubble and were previously shown as literal backslashes.
	clean = clean.replace("\\\n", "\n").replace("\\n", "\n")
	changed = clean != answer
	for name in sorted(known_names, key=len, reverse=True):
		if not name:
			continue
		label = labels.get(name, "")
		pattern = re.compile(rf"(?<![\w]){re.escape(name)}(?![\w])", re.IGNORECASE)
		clean, count = pattern.subn(label or "this field", clean)
		changed = changed or bool(count)
	# Remove any remaining raw snake case token. This avoids showing unrecognized
	# technical names, while preserving ordinary prose and Arabic/French text.
	clean, count = re.subn(r"(?<!\w)[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+(?!\w)", "this field", clean)
	changed = changed or bool(count)
	clean, count = re.subn(r"`([^`]*)`", r"\1", clean)
	changed = changed or bool(count)
	return clean.strip(), changed
