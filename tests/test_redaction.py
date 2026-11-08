"""Unit tests for redaction.py."""

from __future__ import annotations

from redaction import scrub_secrets


def test_scrub_secrets_removes_a_single_secret():
    result = scrub_secrets("Error: key AIzaSyABC123 is invalid", "AIzaSyABC123")

    assert "AIzaSyABC123" not in result
    assert "[REDACTED]" in result


def test_scrub_secrets_removes_multiple_occurrences():
    result = scrub_secrets("key=SECRET, retried with key=SECRET again", "SECRET")

    assert "SECRET" not in result
    assert result.count("[REDACTED]") == 2


def test_scrub_secrets_removes_multiple_distinct_secrets():
    result = scrub_secrets("user=alice token=abc123", "alice", "abc123")

    assert "alice" not in result
    assert "abc123" not in result


def test_scrub_secrets_leaves_text_unchanged_when_secret_absent():
    result = scrub_secrets("Network timeout", "some-key")

    assert result == "Network timeout"


def test_scrub_secrets_ignores_none_and_empty_secrets():
    result = scrub_secrets("Network timeout", None, "")

    assert result == "Network timeout"


def test_scrub_secrets_no_secrets_given_returns_original_text():
    assert scrub_secrets("plain text") == "plain text"
