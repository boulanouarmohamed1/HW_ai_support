import frappe
from frappe.tests import IntegrationTestCase

from hw_ai_support.api import chat


class TestChatAPI(IntegrationTestCase):
	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_guest_is_rejected(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			chat("What is a Sales Order?")

	def test_empty_message_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			chat("  ")

	def test_oversized_history_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			chat("What is a Sales Order?", history=[{"role": "user", "content": "x" * 4001}])
