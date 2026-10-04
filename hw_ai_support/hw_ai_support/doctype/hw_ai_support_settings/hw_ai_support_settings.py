from __future__ import annotations
import frappe
from frappe.model.document import Document

class HWAISupportSettings(Document):
	def validate(self):
		if self.business_data_mode == "Hosted LLM, aggregated results only" and self.hosted_consent:
			self.consented_by = frappe.session.user
			self.consented_on = frappe.utils.now_datetime()

