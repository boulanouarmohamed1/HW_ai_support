# HW AI Support

HW AI Support is a custom Frappe app that adds a multilingual AI support page to ERPNext. It explains ERPNext workflows using permission-filtered site metadata and bundled reference material (Phase 1), and can answer a limited set of questions with live, read-only ERP data (Phase 2).

The app is designed for ERPNext v16 and does not modify Frappe or ERPNext core files. It does not create, update, submit, cancel, or delete business records. The model cannot query the database directly: the server executes only registered tools after checking the current user's permissions.

## What it supports

- English, French, and Arabic question and answer flows. Arabic chat messages render right-to-left.
- Site-specific explanations of permitted DocTypes, visible fields, workflows, and Desk locations, plus local lexical RAG over the bundled ERPNext reference PDF and a curated operational Markdown guide. Query matching expands common English/French/Arabic ERPNext terms and normalizes accents, Arabic variants, and plurals.
- Phase 2 live answers for item search and stock balance, overdue Sales/Purchase Invoices, submitted sales totals, and the Profit and Loss Statement.
- Gemini hosted models and OpenAI-compatible endpoints, including a local endpoint such as Ollama.
- Server-side chat interaction logging, rate limits, a daily call budget, and configurable log retention.

The assistant redirects unrelated questions and should report when grounded information or user permission is unavailable rather than inventing a process or business figure. The LLM is an external service when a hosted provider is selected; review the consent and data handling settings before enabling hosted business-data answers.

## Requirements

- A Frappe bench with ERPNext v16 installed.
- Python dependencies declared in `pyproject.toml`; Bench manages Frappe dependencies. Node.js/Yarn are needed to build Desk assets.
- A reachable configured language model for answers. Business-data tools also require explicit administrator configuration and consent for hosted mode.

## Install or update

For a new installation, fetch the app and install it on the site:

```bash
cd ~/frappe-bench
bench get-app https://github.com/boulanouarmohamed1/HW_ai_support.git
bench --site development.localhost install-app hw_ai_support
```

For an existing installation, skip `get-app` and `install-app`. After installing or updating app files, run:

```bash
cd ~/frappe-bench
bench --site development.localhost migrate
bench build --app hw_ai_support
bench --site development.localhost clear-cache
```

Start the development bench in one terminal with `bench start`. If it is already running, use Ctrl+C in that terminal before starting another copy; duplicate Bench processes can contend for Redis and web ports. Open `http://development.localhost:8000/app/hw-ai-chat` and hard-refresh the page after building assets.

## Configure an LLM

The API credential belongs in the site's private configuration, never in JavaScript, source control, screenshots, or chat messages. See [LLM setup](docs/llm_setup.md) for provider setup, connectivity checks, and troubleshooting.

1. Set the provider and model credential/configuration.
2. Open **HW AI Support Settings** in Desk and select the provider.
3. For Phase 2, have a System Manager enable tools and select a business-data mode. Hosted mode requires explicit consent; local-only mode requires a reachable local endpoint.
4. Check the configured provider from the Bench:

   ```bash
   bench --site development.localhost execute hw_ai_support.llm.ping
   ```

## Documentation

- [Architecture and data flow](docs/architecture.md)
- [LLM setup and troubleshooting](docs/llm_setup.md)
- [User guide in English, French, and Arabic](docs/user_guide.md)
- [Supported tools and boundaries](docs/tools_and_scope.md)
- [Manual test cases](docs/manual_test_cases.md)
- [Project requirement traceability](docs/requirements_traceability.md)

## Current scope

The implemented live-data tools are limited to the list in [Supported tools and boundaries](docs/tools_and_scope.md). Employee leave balance, payroll, generic arbitrary reports, and actions that write business records are not implemented in this release. The project brief describes actions as a later possibility; the current code intentionally remains read-only.
