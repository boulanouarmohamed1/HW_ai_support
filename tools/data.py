from __future__ import annotations

import frappe


def _check(doctype: str, ptype: str, user: str) -> None:
    if not frappe.has_permission(doctype, ptype, user=user):
        raise frappe.PermissionError()


def search_items(query: str, user: str) -> dict:
    _check("Item", "read", user)
    query = (query or "").strip()[:100]
    rows = frappe.get_list(
        "Item",
        filters={"disabled": 0},
        or_filters=[
            ["item_name", "like", f"%{query}%"],
            ["name", "like", f"%{query}%"],
        ],
        fields=["name", "item_name"],
        limit=5,
    )
    return {"candidates": rows}


def get_stock_balance(item_code: str, user: str, warehouse: str | None = None) -> dict:
    _check("Bin", "read", user)
    _check("Item", "read", user)
    _check("Warehouse", "read", user)
    filters = {"item_code": item_code}
    if warehouse:
        filters["warehouse"] = warehouse
    rows = frappe.get_list(
        "Bin",
        filters=filters,
        fields=["warehouse", "actual_qty"],
        limit=20,
    )
    return {
        "item_code": item_code,
        "total_quantity": sum(float(row.actual_qty or 0) for row in rows),
        "warehouses": [{"warehouse": row.warehouse, "actual_qty": float(row.actual_qty or 0)} for row in rows],
    }

    
def get_overdue_invoices(user: str, invoice_type: str = "Sales Invoice") -> dict:
    _check(invoice_type, "read", user)
    party_field = "customer" if invoice_type == "Sales Invoice" else "supplier"
    rows = frappe.get_list(
        invoice_type,
        filters={"docstatus": 1, "status": "Overdue"},
        fields=["outstanding_amount", "due_date", party_field],
        limit=20,
    )
    return {
        "count": len(rows),
        "total_outstanding": sum(float(row.outstanding_amount or 0) for row in rows),
        "oldest_due_date": min((row.due_date for row in rows if row.due_date), default=None),
        "top_parties": [getattr(row, party_field, None) for row in rows[:5]],
    }


def get_sales_summary(from_date: str, to_date: str, user: str) -> dict:
    _check("Sales Invoice", "read", user)
    rows = frappe.get_list(
        "Sales Invoice",
        filters={"docstatus": 1, "posting_date": ["between", [from_date, to_date]]},
        fields=["base_grand_total"],
        limit=20,
    )
    return {
        "from_date": from_date,
        "to_date": to_date,
        "invoice_count": len(rows),
        "total": sum(float(row.base_grand_total or 0) for row in rows),
    }
