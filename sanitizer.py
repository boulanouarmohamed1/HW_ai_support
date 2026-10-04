from __future__ import annotations
import re
from collections.abc import Iterable

def sanitize(answer: str, known_names: set[str], labels: dict[str, str] | None = None, protected_values: Iterable[str] | None = None) -> tuple[str, bool]:
	labels = labels or {}
	clean = re.sub(r"\x60\x60\x60[\s\S]*?\x60\x60\x60", "", answer).strip()
	clean = clean.replace("\\\n", "\n").replace("\\n", "\n")
	changed = clean != answer
	protected = {}
	for index, value in enumerate(protected_values or ()):
		if not isinstance(value, str) or not value or value not in clean:
			continue
		key = "__HW_VALUE_{}_{}".format(index, "__")
		protected[key] = value
		clean = clean.replace(value, key)
	for name in sorted(known_names, key=len, reverse=True):
		if not name:
			continue
		label = labels.get(name, "")
		pattern = re.compile(rf"(?<![\w]){re.escape(name)}(?![\w])", re.IGNORECASE)
		clean, count = pattern.subn(label or "this field", clean)
		changed = changed or bool(count)
	clean, count = re.subn(r"(?<!\w)[A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+(?!\w)", "this field", clean)
	changed = changed or bool(count)
	for key, value in protected.items():
		clean = clean.replace(key, value)
	return clean.strip(), changed
