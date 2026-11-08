"""One place that talks to the LLM providers (DeepSeek first, Groq as fallback).  Sync `requests`: only call from Celery."""
import logging
import re
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class Completion:
    text: str
    model: str
    tokens: int = 0


def _providers():
    return [("DeepSeek", settings.DEEPSEEK_MODEL, "https://api.deepseek.com/chat/completions", settings.DEEPSEEK_API_KEY),
            ("Groq", settings.GROQ_MODEL, "https://api.groq.com/openai/v1/chat/completions", settings.GROQ_API_KEY)]


def complete(messages, max_tokens=1000, temperature=0.7, timeout=20):
    """Return a Completion, or None when no provider is configured/reachable."""
    for name, model, url, key in _providers():
        if not key:
            continue
        try:
            resp = requests.post(url, json={"model": model, "messages": messages, "max_tokens": max_tokens,
                                            "temperature": temperature},
                                 headers={"Authorization": f"Bearer {key}"}, timeout=timeout)
            resp.raise_for_status()
            body = resp.json()
            text = re.sub(r"<think>.*?</think>", "", body["choices"][0]["message"]["content"], flags=re.DOTALL).strip()
            if text:
                return Completion(text, f"{name} ({model})", body.get("usage", {}).get("total_tokens", 0))
        except Exception as exc:
            logger.warning("AI provider %s failed: %s", name, exc)
    return None
