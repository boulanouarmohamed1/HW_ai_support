import frappe
from frappe.tests import IntegrationTestCase

from hw_ai_support.knowledge import build_doctype_doc, clear_knowledge_cache, get_accessible_doctypes
from hw_ai_support.retrieval import detect_language
from hw_ai_support.sanitizer import sanitize


class TestKnowledge(IntegrationTestCase):
	def test_sales_order_uses_labels_not_fieldnames(self):
		if not frappe.db.exists("DocType", "Sales Order"):
			self.skipTest("ERPNext Sales Order is unavailable")
		text = build_doctype_doc("Sales Order", "Administrator", "en")
		self.assertIn("Sales Order", text)
		self.assertIn("Customer", text)
		self.assertNotIn("customer_name", text)

	def test_restricted_user_does_not_get_sales_order(self):
		clear_knowledge_cache()
		accessible = get_accessible_doctypes("Guest")
		self.assertNotIn("Sales Order", [entry["name"] for entry in accessible])

	def test_sanitizer_replaces_known_internal_name(self):
		answer, changed = sanitize("Use cost_center on Sales Order.", {"cost_center", "Sales Order"}, {"cost_center": "Cost Center", "Sales Order": "Sales Order"})
		self.assertTrue(changed)
		self.assertIn("Cost Center", answer)
		self.assertNotIn("cost_center", answer)

	def test_language_detection_including_arabic(self):
		self.assertEqual(detect_language("كيف أنشئ فاتورة؟"), "ar")
		self.assertEqual(detect_language("Comment créer un devis ?"), "fr")
		self.assertEqual(detect_language("How do I create an invoice?"), "en")
