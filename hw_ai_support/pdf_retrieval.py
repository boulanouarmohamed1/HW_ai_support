"""Retrieve relevant passages from the bundled ERPNext documentation PDF."""

from __future__ import annotations

from pathlib import Path

import frappe

from hw_ai_support.pdf_vector_store import retrieve_pdf_chunks

PDF_PATH = Path(__file__).resolve().parent / "resources" / "ERPNext_Documentation_and_Use_Cases.pdf"


def retrieve_pdf_context(question: str, keywords: list[str] | None = None) -> str:
	"""Build or reuse the site's local PDF index and return grounded passages."""
	if not PDF_PATH.is_file():
		return ""
	query = " ".join([question, *(keywords or [])])
	index_path = Path(frappe.get_site_path("private", "files", "hw_ai_support_erpnext_docs.sqlite3"))
	try:
		hits = retrieve_pdf_chunks(query, pdf_path=PDF_PATH, db_path=index_path, limit=5)
	except Exception:
		frappe.log_error(title="HW AI Support PDF retrieval error", message=frappe.get_traceback())
		return ""
	return "\n\n".join(
		f"ERPNext documentation PDF, page {hit['page']}:\n{hit['text']}"
		for hit in hits
	)
