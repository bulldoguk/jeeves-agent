# Tier 2 judgment calls happen inside watchers, not in the poll loop

The poll loop is deliberately kept simple — it runs watchers and diffs their output against open issues. Routing ambiguous Tier 1 flags through a separate Ollama pass would require a two-stage issue type and a more complex loop. Instead, watchers that need judgment call an `ollama_client` directly, using a thin `jeeves/ollama_client.py` (raw `requests` — no `ollama` library dependency). Watchers that don't need Ollama receive the client and ignore it. The poll loop stays unchanged.

`ollama_client` is `None` when `OLLAMA_URL` is not configured — Jeeves runs as Tier 1-only in that case, with no "unavailable" issue raised. The "Tier 2 unavailable" issue is reserved for when Ollama is configured but unreachable. This allows Jeeves to run usefully before dedicated Ollama hardware is available; setting `OLLAMA_URL` later activates Tier 2 with no code changes.

## Considered Options

- **Two-pass loop (Tier 1 flags → Ollama → Issue)** — rejected: requires a new "candidate issue" type and complicates the poll loop for a concern that belongs inside the watcher that has the context.
- **`ollama` Python library** — rejected: the call surface is a single POST endpoint; the library adds install footprint inside the Docker image for no meaningful benefit over `requests`, which is already a dependency.
