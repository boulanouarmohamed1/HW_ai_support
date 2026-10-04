from __future__ import annotations
import frappe
from .base import ToolSpec
from .data import search_items, get_stock_balance, get_overdue_invoices, get_sales_summary

_SPECS=[
 ToolSpec("search_items","Find permitted items by code or name.",{"type":"object","properties":{"query":{"type":"string","maxLength":140}},"required":["query"],"additionalProperties":False},search_items),
 ToolSpec("get_stock_balance","Get permitted stock for one item.",{"type":"object","properties":{"item_code":{"type":"string","maxLength":140},"warehouse":{"type":"string","maxLength":140}},"required":["item_code"],"additionalProperties":False},get_stock_balance),
 ToolSpec("get_overdue_invoices","Summarize permitted overdue invoices.",{"type":"object","properties":{"invoice_type":{"type":"string","enum":["Sales Invoice","Purchase Invoice"]}},"additionalProperties":False},get_overdue_invoices),
 ToolSpec("get_sales_summary","Summarize permitted sales for a period.",{"type":"object","properties":{"from_date":{"type":"string"},"to_date":{"type":"string"}},"required":["from_date","to_date"],"additionalProperties":False},get_sales_summary),
]
def all_tools(): return list(_SPECS)
def get_tool(name): return next((tool for tool in _SPECS if tool.name==name),None)
for tool in _SPECS:
	if not tool.read_only: raise RuntimeError("Only read-only tools are allowed")
