import requests


class OllamaClient:
    """Thin wrapper around the Ollama REST API for Tier 2 judgment calls."""

    def __init__(self, base_url, model):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def judge(self, prompt):
        """Send a prompt and return the response text.

        Raises on network error or non-2xx response — callers should catch
        and treat as Tier 2 unavailable.
        """
        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
