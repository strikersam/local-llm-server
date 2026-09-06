"""tests/test_governance_audit_pii.py — PII redaction in the audit scrubber.

`scrub()` has always stripped *secrets* (tokens, API keys, connection URIs).
These tests cover the narrower PII layer added alongside it: a US SSN and a
Luhn-valid payment-card number must not survive into a stored audit row, while
the values deliberately left alone — email, phone, and non-card long numbers —
must pass through so the audit trail stays debuggable and low-noise.
"""
from __future__ import annotations

import pytest

from packages.governance.audit import AuditEvent, _luhn_ok, scrub


class TestLuhn:
    def test_valid_card_passes(self):
        # 4111 1111 1111 1111 is the canonical Visa test PAN (Luhn-valid).
        assert _luhn_ok("4111111111111111") is True

    def test_invalid_number_fails(self):
        assert _luhn_ok("4111111111111112") is False


class TestSSNRedaction:
    def test_hyphenated_ssn_redacted(self):
        assert "123-45-6789" not in scrub("SSN is 123-45-6789 on file")

    def test_spaced_ssn_redacted(self):
        assert "123 45 6789" not in scrub("ssn 123 45 6789")

    def test_bare_nine_digits_left_alone(self):
        # A bare run of nine digits is too collision-prone to redact.
        text = "order 123456789 shipped"
        assert scrub(text) == text


class TestCardRedaction:
    def test_luhn_valid_card_redacted(self):
        for candidate in ("4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111"):
            assert "4111" not in scrub(f"card {candidate} exp"), candidate

    def test_non_luhn_long_number_left_alone(self):
        # A 16-digit order ref / snowflake that fails Luhn must survive.
        text = "ref 1234567890123456 queued"
        assert scrub(text) == text


class TestNonPIIPreserved:
    def test_email_preserved(self):
        text = "contact owner@example.com about this"
        assert scrub(text) == text

    def test_phone_preserved(self):
        text = "call (555) 123-4567 today"
        assert scrub(text) == text


class TestNestedAndEventIntegration:
    def test_pii_scrubbed_inside_nested_structure(self):
        cleaned = scrub({"note": {"ssn": "123-45-6789", "keep": "hello"}})
        # The `ssn` key matches no secret marker, so the value is scrubbed by
        # the text pass, not the key pass — proving PII redaction runs on values.
        assert "123-45-6789" not in str(cleaned)
        assert "hello" in str(cleaned)

    def test_secrets_still_redacted_alongside_pii(self):
        cleaned = scrub("token=abcdefgh12345678 and ssn 123-45-6789")
        assert "123-45-6789" not in cleaned
        assert "abcdefgh12345678" not in cleaned

    def test_audit_event_scrubs_pii_in_arguments(self):
        event = AuditEvent(arguments={"payload": "customer 4111 1111 1111 1111"})
        assert "4111" not in str(event.arguments["payload"])
