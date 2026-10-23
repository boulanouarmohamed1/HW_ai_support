# Supported tools and boundaries

Phase 2 tools are read-only server functions. The LLM can request only tools registered by the app. The server validates every name and argument and checks the logged-in user's ERPNext permission before reading data. Tools do not create, update, submit, cancel, or delete documents.

| User-facing capability | Data returned | Requirements and limits |
|---|---|---|
| Find an item | Up to five matching item codes and names | The user must have read access to Items. Ambiguous matches should be clarified before querying a balance. |
| Check stock balance | Current on-hand quantity and unit of measure; optional warehouse filter | Requires read access to Item and Bin; Warehouse read access is also checked if a warehouse is specified. Without a warehouse, the app sums visible Bin quantities across warehouses, subject to a result cap. |
| Find overdue invoices | Count, outstanding totals grouped by currency, and oldest due date | Supports submitted Sales Invoices or Purchase Invoices with ERPNext status `Overdue` and a positive outstanding amount. Requires read permission on the selected invoice DocType. Hosted mode sends aggregates, not invoice-level rows, to the model. |
| Summarize sales | Submitted Sales Invoice count and base-currency total for an exact date range | Uses the logged-in user's default Company, when configured, and Sales Invoice read permission. The total uses ERPNext's base grand total. |
| Read Profit and Loss | Summary metrics from ERPNext's built-in Profit and Loss Statement for an exact date range | Uses the logged-in user's default Company and ERPNext's report implementation. `get_report_data` is allow-listed to this report only; arbitrary report execution is not supported. |

The Python registry currently contains `search_items`, `get_stock_balance`, `get_overdue_invoices`, `get_sales_summary`, `get_profit_summary`, and `get_report_data`. The last two both read the built-in Profit and Loss Statement through the app's report adapter.

## Business-data modes

- **Disabled**: no Phase 2 business-data answers.
- **Local LLM only**: tools are allowed only with the configured OpenAI-compatible local endpoint.
- **Hosted LLM, aggregated results only**: requires explicit System Manager consent. Compact results are passed to the hosted provider so it can summarize them.

Tools must also be enabled. Provider setup is documented in [LLM setup](llm_setup.md).

## Not currently supported

- Employee leave balances, absence lists, employee payroll or salary information.
- Generic reports or arbitrary database questions.
- Record creation or changes, including quotations, invoices, stock adjustments, and payments.
- General-purpose questions outside ERPNext.

For unsupported requests, the assistant should explain the limitation or redirect to ERPNext support. It must not invent values or imply that it changed a record.
