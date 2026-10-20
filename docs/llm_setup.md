# Language model setup

The provider implementation stays in `hw_ai_support/llm.py`; no model call runs in the browser.

## Gemini

Store credentials in site configuration and select Gemini in **HW AI Support Settings**:

```bash
bench --site development.localhost set-config gemini_api_key "<YOUR_ROTATED_KEY>"
bench --site development.localhost set-config gemini_model "gemini-2.5-flash"
bench --site development.localhost clear-cache
bench --site development.localhost execute hw_ai_support.llm.ping
```

For Phase 2, a System Manager must check **Tools Enabled**, select **Hosted LLM, aggregated results only**, and check **Hosted Consent**. This choice permits the question, conversation context, and aggregate business results to be sent to Gemini. Turn it off to disable business-data answers.

## Local OpenAI-compatible endpoint

In **HW AI Support Settings**, choose provider `openai_compatible`, set the base URL and model name, and choose **Local LLM only**. Example base URL for Ollama is `http://localhost:11434/v1`. The server uses `/chat/completions`, sends the read-only tool schemas, and does not send business records until a server-side tool call has passed permission checks. A key is optional for a localhost endpoint. For a remote compatible endpoint, store `openai_api_key` in site config or set `OPENAI_API_KEY` in the bench server environment.

After changing provider settings, use the same `bench execute ... ping` command. It returns only provider/model and a generic diagnostic. Inspect **Error Log** on the bench for the provider failure detail; never copy API keys into logs, issues, or source control.

Both providers use a bounded request timeout and configurable output token limit (`hw_ai_max_output_tokens` site config, default 1024). Provider errors shown to users are generic and localized.
