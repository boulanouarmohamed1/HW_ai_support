from __future__ import annotations
import frappe
from .registry import get_tool

def execute_tool(name: str, arguments: dict, user: str | None = None) -> dict:
	user=user or frappe.session.user
	if user=="Guest": return {"status":"denied","meta":{},"message_key":"no_access"}
	spec=get_tool(name)
	if not spec or not isinstance(arguments,dict): return {"status":"invalid_args","meta":{},"message_key":"invalid_tool"}
	if any(k not in spec.parameters.get("properties",{}) for k in arguments): return {"status":"invalid_args","meta":{},"message_key":"invalid_tool"}
	try:
		return {"status":"ok","meta":{},"data":spec.handler(user=user,**arguments)}
	except frappe.PermissionError:
		return {"status":"denied","meta":{},"message_key":"no_access"}
	except Exception:
		frappe.log_error(title="HW AI Support tool error",message=frappe.get_traceback())
		return {"status":"error","meta":{},"message_key":"tool_error"}
