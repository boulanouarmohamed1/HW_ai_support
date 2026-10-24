"""Permission aware, read-only ERPNext data."""

from __future__ import annotations

import frappe


def _check(doctype: str, ptype: str, user: str) -> None:
	if user != frappe.session.user or not frappe.has_permission(doctype, ptype, user=user):
		raise frappe.PermissionError()


def _date_filters(from_date: str, to_date: str) -> dict:
	return {"posting_date": ["between", [from_date, to_date]], "docstatus": 1}


def search_items(query: str, user: str) -> dict:
	_check("Item", "read", user)
	query = (query or "").strip()[:100]
	if not query:
		return {"candidates": []}
	rows = frappe.get_list("Item", filters={"disabled": 0}, or_filters=[["item_name", "like", f"%{query}%"], ["name", "like", f"%{query}%"]], fields=["name", "item_name"], limit_page_length=5)
	return {"candidates": rows}


def get_stock_balance(item_code: str, user: str, warehouse: str | None = None) -> dict:
	_check("Item", "read", user)
	if not frappe.db.exists("Item", item_code):
		return {"found": False, "item_code": item_code}
	filters = {"item_code": item_code}
	if warehouse:
		_check("Warehouse", "read", user)
		if not frappe.db.exists("Warehouse", warehouse):
			return {"found": False, "item_code": item_code}
		filters["warehouse"] = warehouse
	_check("Bin", "read", user)
	rows = frappe.get_list("Bin", filters=filters, fields=["warehouse", "actual_qty"], limit_page_length=501)
	if len(rows) > 500:
		return {"found": True, "complete": False, "item_code": item_code, "message": "Warehouse result cap reached; total is unavailable."}
	return {"found": True, "item_code": item_code, "stock_uom": frappe.db.get_value("Item", item_code, "stock_uom"), "total_quantity": sum(float(row.actual_qty or 0) for row in rows), "warehouses": [{"warehouse": row.warehouse, "actual_qty": float(row.actual_qty or 0)} for row in rows]}


def get_overdue_invoices(user: str, invoice_type: str = "Sales Invoice") -> dict:
	if invoice_type not in {"Sales Invoice", "Purchase Invoice"}:
		raise ValueError("Unsupported invoice type")
	_check(invoice_type, "read", user)
	party_field = "customer" if invoice_type == "Sales Invoice" else "supplier"
	rows = frappe.get_list(invoice_type, filters={"docstatus": 1, "status": "Overdue", "outstanding_amount": [">", 0]}, fields=["name", "outstanding_amount", "due_date", party_field, "currency"], order_by="due_date asc", limit_page_length=5001)
	if len(rows) > 5000:
		return {"complete": False, "count_at_least": 5001, "message": "Invoice result cap reached; totals are unavailable."}
	totals_by_currency = {}
	for row in rows:
		currency = row.currency or "Unknown currency"
		totals_by_currency[currency] = totals_by_currency.get(currency, 0) + float(row.outstanding_amount or 0)
	return {"count": len(rows), "totals_by_currency": totals_by_currency, "oldest_due_date": min((str(row.due_date) for row in rows if row.due_date), default=None), "invoices": [{"invoice": row.name, "due_date": str(row.due_date) if row.due_date else None, "outstanding": float(row.outstanding_amount or 0), "currency": row.currency} for row in rows[:20]]}


def get_sales_summary(from_date: str, to_date: str, user: str) -> dict:
	_check("Sales Invoice", "read", user)
	company = frappe.defaults.get_user_default("Company")
	filters = _date_filters(from_date, to_date)
	if company:
		filters["company"] = company
	rows = frappe.get_list("Sales Invoice", filters=filters, fields=["base_grand_total", "currency"], limit_page_length=5001)
	if len(rows) > 5000:
		return {"complete": False, "count_at_least": 5001, "from_date": from_date, "to_date": to_date, "message": "Sales result cap reached; total is unavailable."}
	return {"from_date": from_date, "to_date": to_date, "invoice_count": len(rows), "total": sum(float(row.base_grand_total or 0) for row in rows), "currency": frappe.get_cached_value("Company", company, "default_currency") if company else None, "note": "Totals are in company base currency."}


def get_profit_summary(from_date: str, to_date: str, user: str) -> dict:
	"""Use ERPNext's own report, retaining its permission and accounting logic."""
	if user != frappe.session.user or not frappe.db.exists("Report", "Profit and Loss Statement"):
		raise frappe.PermissionError()
	company = frappe.defaults.get_user_default("Company")
	if not company:
		return {"available": False, "reason": "no_default_company"}
	from frappe.desk.query_report import run

	result = run("Profit and Loss Statement", filters={"company": company, "filter_based_on": "Date Range", "period_start_date": from_date, "period_end_date": to_date, "periodicity": "Yearly", "selected_view": "Report", "accumulated_values": 0, "include_default_book_entries": 1})
	summary = [{"metric": str(row.get("label") or "Profit and Loss"), "amount": float(row.get("value") or 0)} for row in (result.get("report_summary") or []) if isinstance(row, dict) and "profit" in str(row.get("label") or "").lower()]
	return {"from_date": from_date, "to_date": to_date, "currency": frappe.get_cached_value("Company", company, "default_currency"), "summary": summary, "available": bool(summary)}


def get_report_data(report_name: str, from_date: str, to_date: str, user: str) -> dict:
	"""Execute only the report explicitly allow-listed for business insight."""
	if report_name != "Profit and Loss Statement":
		raise ValueError("This report is not allow-listed")
	return get_profit_summary(from_date=from_date, to_date=to_date, user=user)
