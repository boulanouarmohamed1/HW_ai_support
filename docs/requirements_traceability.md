# Project brief traceability

This page maps the HW AI Support brief to the current source tree. “Implemented” describes code present in this app; it does not mean every acceptance scenario has been run against a live ERPNext site. Follow [manual test cases](manual_test_cases.md) for validation.

| Brief requirement | Current implementation | Status / validation |
|---|---|---|
| Installable custom app named `hw_ai_support` for ERPNext v16, with no core modifications | Frappe app package and Desk Page live in this repository; ERPNext is a required app | Implemented; install/update steps are in the root README. |
| Desk chat interface using the existing Vue 3 frontend stack | `public/js/components/HWAIChat.vue`, loaded by the Desk page | Implemented; page route is `/app/hw-ai-chat`. |
| English, French, and Arabic interactions, with Arabic right-to-left chat rendering | Language detection and localized prompts; French/Arabic app translations; Vue sets RTL for Arabic | Implemented; validate each language with the manual test cases. |
| Phase 1: explain DocTypes, workflows, how-to guidance, and Desk locations from the installed site | Permission-filtered live metadata (`frappe.get_meta()`), workflow/workspace context, and bundled ERPNext reference PDF retrieval | Implemented within retrieved/available context; unsupported answers must state the limitation. |
| Use natural phrasing instead of raw internal field names | Human labels in metadata context, answer policy, and output sanitizer | Implemented as guardrails; verify with the raw-name prompt-injection and multilingual test cases. |
| Phase 2: tool calls for stock and reports, with short natural summaries | Allow-listed item search, stock balance, overdue invoice summary, sales summary, and Profit and Loss report tools | Implemented for the scope listed in [tools and boundaries](tools_and_scope.md). |
| Every read uses the logged-in user's permissions; no AI superuser shortcut | Authenticated chat method, identity matching in tool handlers, Frappe permission checks, permission-aware list/report APIs | Implemented; verify allowed and denied users with manual test cases. |
| No fabricated answers or unrelated general-purpose behavior | System prompts, retrieved site context, grounded tool summaries, and out-of-scope routing | Implemented as policy and validation; verify with the no-context and unrelated-question cases. |
| No destructive action in this release | Tool registry is checked to contain read-only specs; no write handler is registered | Implemented. Any future write feature requires a separate design and authorization flow. |
| Log AI interactions | Chat API writes interaction outcomes to AI Interaction Log; provider failures have Frappe Error Log entries; retention cleanup is scheduled | Implemented for requests reaching the chat handler; verify audit entries and configured retention on the site. |
| README, architecture/data-flow overview, and provider setup | Root README and `docs/architecture.md` / `docs/llm_setup.md` | Delivered. |
| Supported tool/action list and EN/FR/AR user guide | `docs/tools_and_scope.md` and `docs/user_guide.md` | Delivered. |
| Manual tests and permission/security validation | `docs/manual_test_cases.md` | Test plan delivered; site-specific test execution remains necessary. |

## Release boundary

The brief describes business insight questions for stock, sales/profit, and invoices. The present implementation covers those classes in the specific forms listed in `tools_and_scope.md`. Employee leave/payroll, arbitrary reports, and record-changing actions are not implemented and should not be represented as available features.
