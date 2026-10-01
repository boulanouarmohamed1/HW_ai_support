# HW AI Support

Phase 1 adds a read-only, permission-aware ERPNext Desk assistant. It explains only the live DocType metadata, fields, workflows and Desk locations available on the current site. It supports English, French and Arabic (including RTL chat rendering).

## Requirements and installation

- ERPNext/Frappe v16; this app declares `erpnext` as a required app.
- A Gemini API key set only in site configuration (never in this repository):

  ```bash
  bench --site <site> set-config gemini_api_key "<KEY>"
  # Optional, when Google changes available models:
  bench --site <site> set-config gemini_model "<MODEL>"
  ```

Then run `bench --site <site> migrate`, `bench build --app hw_ai_support`, and `bench --site <site> clear-cache`. Open **HW AI Support** from the Desk navbar or `/app/hw-ai-chat`.

## Privacy and scope

The hosted provider receives only the question, the recent chat history, and selected DocType metadata (labels/structure/workflow/permissions). It never receives business records, stock values, invoices, passwords, or the API key. Phase 1 cannot read or write business data and cannot perform actions.

## Roadmap

Phase 1 is grounded metadata help. Later phases may add approved business-data tools, streaming, and semantic retrieval after separate security review.
