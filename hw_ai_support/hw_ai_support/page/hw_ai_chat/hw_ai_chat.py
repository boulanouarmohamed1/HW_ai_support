import frappe


@frappe.whitelist()
def ping():
	"""Small Page module marker; chat is served by hw_ai_support.api.chat."""
	return {"ok": True}
