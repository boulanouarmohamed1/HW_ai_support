# HW AI Support

Phase 1 adds a read-only, permission-aware ERPNext Desk assistant. It explains only the live DocType metadata, fields, workflows and Desk locations available on the current site. It supports English, French and Arabic (including RTL chat rendering).

## Requirements

- ERPNext/Frappe v16; this app declares `erpnext` as a required app.
- Node.js 24 for the asset build.
- A Gemini API key, set only in site configuration (never in this repository).

## Install into an existing bench

The following assumes ERPNext v16 and a site already exist. Replace `<bench-path>`, `<site>` and `<KEY>` with the local values. Never commit or paste a real key into Git.

```bash
cd <bench-path>

# Clone the app into this bench and install it on the chosen site.
bench get-app https://github.com/boulanouarmohamed1/HW_ai_support.git --branch V2
bench --site <site> install-app hw_ai_support

# Keep the API key in site config only. This is not stored in the app repository.
bench --site <site> set-config gemini_api_key "<KEY>"

# Optional: choose an available Gemini text model for this Google AI project.
bench --site <site> set-config gemini_model "gemini-2.5-flash"

# Build with Node 24, sync doctypes/pages, and refresh Desk assets.
PATH=/opt/homebrew/opt/node@24/bin:$PATH bench build --app hw_ai_support
bench --site <site> migrate
bench --site <site> clear-cache
bench start
```

Open `http://localhost:8000/app/hw-ai-chat`, or select **HW AI Support** in the Desk sidebar. If a browser holds old assets, hard-refresh with `Cmd + Shift + R`.

## Update an existing development install

```bash
cd <bench-path>/apps/hw_ai_support
git pull origin V2

cd ../..
PATH=/opt/homebrew/opt/node@24/bin:$PATH bench build --app hw_ai_support
bench --site <site> migrate
bench --site <site> clear-cache
```

Run the app test suite before continuing Phase 2 development:

```bash
cd <bench-path>
bench --site <site> set-config allow_tests true
bench --site <site> run-tests --app hw_ai_support
bench --site <site> set-config allow_tests false
```

## Gemini configuration

If a configured Gemini model is unavailable or returns HTTP 429, select a model enabled for the Google AI project and check that project’s quota/billing. The client never exposes provider error details in the Desk UI; technical diagnostics go to Frappe Error Log.

## Privacy and scope

The hosted provider receives only the question, the recent chat history, and selected DocType metadata (labels/structure/workflow/permissions). It never receives business records, stock values, invoices, passwords, or the API key. Phase 1 cannot read or write business data and cannot perform actions.

## Roadmap

Phase 1 is grounded metadata help. Later phases may add approved business-data tools, streaming, and semantic retrieval after separate security review.
