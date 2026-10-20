"""Build permission-aware, metadata-only knowledge at request time."""

from __future__ import annotations

from dataclasses import dataclass, field

import frappe

LAYOUT_TYPES = {"Section Break", "Column Break", "Tab Break", "HTML", "Fold", "Heading", "Button", "Image"}
SYSTEM_MODULES = {"Core", "Custom", "Desk", "Integrations", "Email", "Workflow", "Print", "Website"}


class DoctypeKnowledge(str):
	"""Text sent to the model plus private names used exclusively by sanitizer."""

	def __new__(cls, text: str, known_names: set[str], labels: dict[str, str]):
		obj = super().__new__(cls, text)
		obj.known_internal_names = known_names
		obj.internal_name_labels = labels
		obj.doctype_label = labels.get(next(iter(known_names), ""), "")
		return obj


def _translated(value: str | None, lang: str) -> str:
	return frappe._(value or "", lang=lang)


def _safe_meta(doctype: str):
	return frappe.get_meta(doctype)


def _meta_value(meta, key: str, default=None):
	"""Meta exposes some DocType fields through mapping access in v16."""
	return meta.get(key) or getattr(meta, key, None) or default


def _include(meta) -> bool:
	return not (_meta_value(meta, "issingle", 0) or _meta_value(meta, "istable", 0) or _meta_value(meta, "is_virtual", 0) or _meta_value(meta, "is_virtual_doctype", 0) or _meta_value(meta, "module", "") in SYSTEM_MODULES)


def _cache_key(user: str) -> str:
	return f"hw_ai_support:doctype_index:{user}"


def clear_knowledge_cache(doc=None, method=None) -> None:
	"""Invalidate all user indexes after metadata or workflow changes."""
	try:
		frappe.cache.delete_keys("hw_ai_support:doctype_index:*")
	except Exception:
		frappe.log_error(title="HW AI Support cache invalidation", message=frappe.get_traceback())


def get_accessible_doctypes(user: str) -> list[dict]:
	"""Return only documents the requested user can read, cached one hour per user."""
	cache = frappe.cache
	key = _cache_key(user)
	if cached := cache.get_value(key, shared=True):
		return cached
	entries = []
	for row in frappe.get_list("DocType", fields=["name"], order_by="name", limit_page_length=1000):
		doctype = row.name
		try:
			meta = _safe_meta(doctype)
			if not _include(meta) or not frappe.has_permission(doctype, "read", user=user):
				continue
			entries.append({
				"name": doctype,
				"label": _meta_value(meta, "label", doctype),
				"module": _meta_value(meta, "module", ""),
				"description": (_meta_value(meta, "description") or _meta_value(meta, "search_fields", ""))[:300],
			})
		except Exception:
			# A malformed/custom DocType must never make chat unusable.
			continue
	cache.set_value(key, entries, expires_in_sec=3600, shared=True)
	return entries


def _doctype_label(doctype: str, lang: str) -> str:
	try:
		return _translated(_meta_value(frappe.get_meta(doctype), "label", doctype), lang)
	except Exception:
		return _translated("Related document", lang)


def _workspace_path(doctype: str, module: str, lang: str) -> str:
	"""Find a v16 Workspace Link when available; module is safe fallback."""
	try:
		links = frappe.get_list("Workspace Link", filters={"link_type": "DocType", "link_to": doctype, "hidden": 0}, fields=["parent", "label"], limit_page_length=20)
		for link in links:
			if not frappe.has_permission("Workspace", "read", doc=link.parent):
				continue
			workspace = frappe.get_value("Workspace", link.parent, "label") or link.parent
			return f"{_translated(workspace, lang)} → {_translated(link.label or _doctype_label(doctype, lang), lang)}"
	except Exception:
		pass
	return f"{_translated(module, lang)} → {_doctype_label(doctype, lang)}"


def _workflow_lines(doctype: str, lang: str, names: set[str], labels: dict[str, str]) -> list[str]:
	try:
		workflow_name = frappe.get_meta(doctype).get_workflow()
		if not workflow_name:
			return []
		workflow = frappe.get_doc("Workflow", workflow_name)
		if not workflow.is_active:
			return []
		states = ", ".join(_translated(row.state, lang) for row in workflow.states)
		transitions = []
		for row in workflow.transitions:
			roles = _translated(row.allowed or "permitted roles", lang)
			transitions.append(f"{_translated(row.state, lang)} → {_translated(row.next_state, lang)} ({roles})")
		return [f"Workflow states: {states}.", "Workflow transitions: " + "; ".join(transitions[:12]) + "."]
	except Exception:
		return []


def build_doctype_doc(doctype: str, user: str, lang: str) -> DoctypeKnowledge:
	"""Generate a compact metadata document; no business document is ever queried."""
	meta = _safe_meta(doctype)
	label = _translated(_meta_value(meta, "label", doctype), lang)
	names, labels = {doctype}, {doctype: label}
	module = _meta_value(meta, "module", "")
	description = _meta_value(meta, "description")
	search_fields = _meta_value(meta, "search_fields")
	lines = [f"Document: {label}.", f"Module: {_translated(module, lang)}."]
	if description:
		lines.append(f"Description: {_translated(description, lang)}")
	elif search_fields:
		search_labels = []
		for fieldname in search_fields.split(","):
			field = meta.get_field(fieldname.strip())
			if field and field.label:
				search_labels.append(_translated(field.label, lang))
		if search_labels:
			lines.append("Useful information can be searched by: " + ", ".join(search_labels) + ".")
	lines.append("Lifecycle: draft → submitted → cancelled." if _meta_value(meta, "is_submittable", 0) else "This document is not submitted; it is saved as a draft record.")
	lines.append("Location in Desk: " + _workspace_path(doctype, module, lang) + ".")

	field_descriptions = []
	for df in meta.fields:
		if df.fieldtype in LAYOUT_TYPES or df.hidden or not df.label:
			continue
		field_label = _translated(df.label, lang)
		names.add(df.fieldname)
		labels[df.fieldname] = field_label
		detail = field_label + (" (required)" if df.reqd else "")
		if df.fieldtype == "Select" and df.options:
			detail += ": " + ", ".join(_translated(option, lang) for option in df.options.split("\n") if option)[:300]
		elif df.fieldtype in {"Link", "Table", "Table MultiSelect"} and df.options:
			if frappe.has_permission(df.options, "read", user=user):
				names.add(df.options)
				target = _doctype_label(df.options, lang)
				labels[df.options] = target
				detail += f" → {target}"
			else:
				detail += f" → {_translated('a restricted document', lang)}"
		elif df.fieldtype == "Dynamic Link":
			# `options` is the controlling *fieldname*, not a DocType (for example,
			# Quotation's Party uses the value selected in Quotation To). Never pass
			# it to get_meta(), which would create a misleading "DocType not found".
			controller = meta.get_field(df.options) if df.options else None
			controller_label = _translated(controller.label, lang) if controller and controller.label else _translated("Document type", lang)
			if df.options:
				names.add(df.options)
				labels[df.options] = controller_label
			detail += f" → {_translated('document chosen in', lang)} {controller_label}"
		field_descriptions.append(detail)
	if field_descriptions:
		lines.append("Visible fields: " + "; ".join(field_descriptions[:45]) + ".")

	outgoing = []
	for df in meta.fields:
		if df.fieldtype in {"Link", "Table", "Table MultiSelect"} and df.options:
			outgoing.append(_doctype_label(df.options, lang))
	if outgoing:
		lines.append("Links to: " + ", ".join(list(dict.fromkeys(outgoing))[:20]) + ".")
	try:
		incoming_rows = frappe.get_list("DocField", filters={"fieldtype": "Link", "options": doctype}, fields=["parent"], limit_page_length=50)
		incoming = [_doctype_label(row.parent, lang) for row in incoming_rows if row.parent and frappe.has_permission(row.parent, "read", user=user)]
		if incoming:
			lines.append("Referenced by: " + ", ".join(dict.fromkeys(incoming)) + ".")
	except Exception:
		pass
	lines.extend(_workflow_lines(doctype, lang, names, labels))
	permissions = [ptype for ptype in ("read", "create", "write", "submit", "cancel") if frappe.has_permission(doctype, ptype, user=user)]
	lines.append("This user may: " + (", ".join(permissions) if permissions else "no actions") + ".")

	# Preserve the essential identity, fields and permissions first.
	text = "\n".join(lines)
	if len(text) > 3000:
		text = text[:2997].rsplit(" ", 1)[0] + "..."
	knowledge = DoctypeKnowledge(text, names, labels)
	knowledge.doctype_label = label
	return knowledge
