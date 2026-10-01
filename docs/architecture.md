# Architecture

```mermaid
flowchart LR
  U[Desk chat] --> N[Language and scope normalization]
  N --> R[Permission-aware lexical retrieval]
  R --> M[frappe.get_meta metadata context]
  M --> G[Gemini REST API]
  G --> S[Internal-name sanitizer]
  S --> L[AI Interaction Log]
  S --> U
```

Each request runs as the logged-in Frappe user. Retrieval checks the user's read permission before selecting a DocType, then `frappe.get_meta()` provides the merged standard/custom metadata. No business documents are queried.

## Privacy

In Phase 1, the hosted LLM receives only the question, recent conversation history, and selected Doctype metadata: human labels, visible structure, links, workflow descriptions, Desk location and the user's allowed actions. It does not receive business-record contents, quantities, money, passwords, configuration values, or the Gemini key. The key is used only in the Python backend.
