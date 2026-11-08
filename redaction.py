"""
redaction.py
────────────
Keep secrets out of anything shown to the user or persisted to the DB —
specifically, exception text that might otherwise echo back an API key.
"""

from __future__ import annotations


def scrub_secrets(text: str, *secrets: str | None) -> str:
    """Replace any occurrence of the given secret values in *text* with a
    placeholder. Apply this to any error message before it's displayed or
    stored, since exceptions can embed request details that include a
    secret passed in by the caller."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text
