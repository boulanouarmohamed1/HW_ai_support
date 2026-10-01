# Gemini setup

Create a Gemini API key in your Google AI project, then keep it in site configuration:

```bash
bench --site mysite.local set-config gemini_api_key "<KEY>"
```

`GEMINI_API_KEY` is supported as an environment-variable fallback. Optionally set `gemini_model`; otherwise the app requests `gemini-3.5-flash`. Provider names change, so configure an available model for your account if the configured model returns a model-not-found error.

`hw_ai_support/llm.py` is the sole provider boundary. To use a local gateway later, preserve `ask(system_prompt, messages, json_mode=False)` and replace its HTTP implementation. Do not move model calls into browser code.
