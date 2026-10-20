"""The explicit allow-list of supported, read-only tools."""

from __future__ import annotations

from .base import ToolSpec
from .data import get_overdue_invoices, get_profit_summary, get_report_data, get_sales_summary, get_stock_balance, search_items

_SPECS = [
	ToolSpec("search_items", "Find permitted inventory items by code or name.", {"type": "object", "properties": {"query": {"type": "string", "maxLength": 100}}, "required": ["query"], "additionalProperties": False}, search_items),
	ToolSpec("get_stock_balance", "Read current on-hand stock for one permitted item, optionally in a warehouse.", {"type": "object", "properties": {"item_code": {"type": "string", "maxLength": 140}, "warehouse": {"type": "string", "maxLength": 140}}, "required": ["item_code"], "additionalProperties": False}, get_stock_balance),
	ToolSpec("get_overdue_invoices", "Summarize submitted overdue sales or purchase invoices visible to the current user.", {"type": "object", "properties": {"invoice_type": {"type": "string", "enum": ["Sales Invoice", "Purchase Invoice"]}}, "additionalProperties": False}, get_overdue_invoices),
	ToolSpec("get_sales_summary", "Summarize permitted submitted sales invoices between the requested dates.", {"type": "object", "properties": {"from_date": {"type": "string", "maxLength": 10}, "to_date": {"type": "string", "maxLength": 10}}, "required": ["from_date", "to_date"], "additionalProperties": False}, get_sales_summary),
	ToolSpec("get_profit_summary", "Read the ERPNext Profit and Loss report for the requested dates.", {"type": "object", "properties": {"from_date": {"type": "string", "maxLength": 10}, "to_date": {"type": "string", "maxLength": 10}}, "required": ["from_date", "to_date"], "additionalProperties": False}, get_profit_summary),
	ToolSpec("get_report_data", "Run an allow-listed ERPNext report; currently only Profit and Loss Statement is available.", {"type": "object", "properties": {"report_name": {"type": "string", "enum": ["Profit and Loss Statement"]}, "from_date": {"type": "string", "maxLength": 10}, "to_date": {"type": "string", "maxLength": 10}}, "required": ["report_name", "from_date", "to_date"], "additionalProperties": False}, get_report_data),
]


def all_tools():
	return list(_SPECS)


def get_tool(name: str):
	return next((tool for tool in _SPECS if tool.name == name), None)


if any(not tool.read_only for tool in _SPECS):
	raise RuntimeError("Only read-only tools may be registered")
