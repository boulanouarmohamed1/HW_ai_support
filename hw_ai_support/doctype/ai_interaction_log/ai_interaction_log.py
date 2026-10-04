from frappe.model.document import Document


class AIInteractionLog(Document):
	"""Immutable audit record; inserts are performed by the chat endpoint only."""

