from __future__ import annotations
import frappe
from frappe.utils import add_days, nowdate

def purge_old_logs():
	try:
		settings=frappe.get_single('HW AI Support Settings')
		days=int(settings.log_retention_days or 90)
		for row in frappe.get_list('AI Interaction Log', filters={'creation':['<',add_days(nowdate(),-days)]}, fields=['name'], limit_page_length=500):
			frappe.delete_doc('AI Interaction Log',row.name,ignore_permissions=True)
	except Exception:
		frappe.log_error(title='HW AI Support retention job',message=frappe.get_traceback())
