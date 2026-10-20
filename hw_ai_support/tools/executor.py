"""Validate and execute only registered read-only business insight tools."""

from __future__ import annotations

import frappe
from frappe.utils import getdate

from .registry import get_tool


def _validate_arguments(spec, arguments: dict) -> None:
	parameters = spec.parameters
	properties = parameters.get("properties", {})
	if not isinstance(arguments, dict) or any(key not in properties for key in arguments):
		raise ValueError("Unexpected tool arguments")
	if any(key not in arguments for key in parameters.get("required", [])):
		raise ValueError("Missing tool arguments")
	for key, value in arguments.items():
		definition = properties[key]
		if definition.get("type") == "string":
			if not isinstance(value, str) or len(value) > definition.get("maxLength", 100):
				raise ValueError("Invalid text argument")
			if "enum" in definition and value not in definition["enum"]:
				raise ValueError("Invalid choice")
	if "from_date" in arguments and "to_date" in arguments:
		start, end = getdate(arguments["from_date"]), getdate(arguments["to_date"])
		if str(start) != arguments["from_date"] or str(end) != arguments["to_date"]:
			raise ValueError("Dates must use YYYY-MM-DD")
		if end < start or (end - start).days > 366:
			raise ValueError("Invalid date range")


def execute_tool(name: str, arguments: dict, user: str | None = None) -> dict:
	user = user or frappe.session.user
	if user == "Guest" or user != frappe.session.user:
		return {"status": "denied", "message_key": "no_access"}
	spec = get_tool(name)
	if not spec or not spec.read_only:
		return {"status": "invalid_args", "message_key": "invalid_tool"}
	try:
		_validate_arguments(spec, arguments)
		return {"status": "ok", "data": spec.handler(user=user, **arguments)}
	except (TypeError, ValueError, frappe.ValidationError):
		return {"status": "invalid_args", "message_key": "invalid_tool"}
	except frappe.PermissionError:
		return {"status": "denied", "message_key": "no_access"}
	except Exception:
		frappe.log_error(title="HW AI Support tool error", message=frappe.get_traceback())
		return {"status": "error", "message_key": "tool_error"}
