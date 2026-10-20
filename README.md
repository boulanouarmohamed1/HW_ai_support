# HW AI Support

HW AI Support is a read-only ERPNext v16 assistant for English, French, and Arabic. Phase 1 explains this site's permitted DocTypes, fields, workflows, and Desk locations. Phase 2 adds permission-checked business insight tools for stock, overdue invoices, sales totals, and the ERPNext Profit and Loss report.

The app never writes ERPNext business records. Every tool call is checked server-side against the logged-in user; model output is not treated as permission to read anything. Unsupported employee leave, payroll, or other business questions are not answered with invented figures.

## Requirements

- Frappe and ERPNext v16 installed on a bench.
- Python dependencies from `pyproject.toml`; Node is only needed to build Desk assets.
- One configured LLM: Gemini, or an OpenAI-compatible local server.

## Install or update in a bench

For a new install, clone this app into the bench and install it on the site. If it is already installed, skip those first two commands.

```bash
cd ~/frappe-bench
bench get-app https://github.com/boulanouarmohamed1/HW_ai_support.git
bench --site development.localhost install-app hw_ai_support
```

After copying/updating the app, run:

```bash
cd ~/frappe-bench
bench --site development.localhost migrate
bench build --app hw_ai_support
bench --site development.localhost clear-cache
```

Run the development server in one terminal with `bench start`. If it is already running, stop it with Ctrl+C in that terminal before starting it again; do not launch a second bench against the same Redis/HTTP ports. Open `http://development.localhost:8000/app/hw-ai-chat` and hard refresh the browser.

## Configure the language model

### Gemini hosted service

Keep the API key in site configuration, never in this repository or browser code. Rotate a key if it has been shared in chat or screenshots.

```bash
bench --site development.localhost set-config gemini_api_key "<YOUR_ROTATED_KEY>"
bench --site development.localhost set-config gemini_model "gemini-2.5-flash"
bench --site development.localhost clear-cache
```

In Desk, search for **HW AI Support Settings** and set **LLM Provider** to Gemini. For business insights, a System Manager must also enable **Tools Enabled**, select **Hosted LLM, aggregated results only**, and enable **Hosted Consent**. This explicitly allows the hosted model to receive the question and compact tool aggregates (for example an item stock total or invoice count and amount); it does not receive the underlying invoice rows. Leave tools disabled if hosted processing is not approved.

Check connectivity from the bench:

```bash
bench --site development.localhost execute hw_ai_support.llm.ping
```

### OpenAI-compatible local model

Configure **LLM Provider** as `openai_compatible`, **Local LLM Base URL** (for example `http://localhost:11434/v1`) and **Local LLM Model** in the settings DocType. Then choose **Local LLM only** and enable tools. The local endpoint must be reachable from the bench host. This provider does not require a key for localhost; a remote compatible endpoint uses `openai_api_key` in site config or `OPENAI_API_KEY` in the server environment.

The assistant sends tool schemas to the model. ERPNext records are read only after the model asks for a registered tool, and the handler checks permissions and validates arguments before querying.

## Supported Phase 2 tools

| Tool | What it answers |
|---|---|
| Item search | Resolve an item name or code the user can access |
| Stock balance | Current on-hand total for an item, optionally filtered to a permitted warehouse |
| Overdue invoices | Count and outstanding total for submitted overdue Sales Invoices or Purchase Invoices |
| Sales summary | Submitted sales invoice total and count for a date range, in company base currency |
| Report data | `get_report_data` only accepts the allow-listed Profit and Loss Statement and summarizes its grounded figures |

The tools are read-only. Employee leave balance, payroll, and arbitrary reports are not currently exposed through tools.

## Test questions

Start with one that must read live data:

- `What is the stock for item SKU_001?`
- `Which supplier invoices are overdue?`
- `What were sales from 2026-01-01 to 2026-01-31?`
- `What was the net profit from 2026-01-01 to 2026-01-31?`
- `What is a Sales Order?` (knowledge / Phase 1)
- `How do I create a quotation?` (knowledge / Phase 1)
- `ما هو أمر المبيعات؟` and `Comment créer un devis ?` (language checks)
- `What is the capital of France?` (should politely redirect)

Use dates that exist in the site's accounting periods. The current stock and report values depend on your actual ERPNext data and the logged-in account's permissions.

## Documentation

- [Architecture](docs/architecture.md)
- [LLM setup](docs/llm_setup.md)
- [User guide in English, French, and Arabic](docs/user_guide.md)
- [Manual test cases](docs/manual_test_cases.md)
