"""Massive client: missing key, auth fallback, no key leakage."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import pytest

from src.data.massive_client import (
    MassiveAuthError,
    MassiveFuturesClient,
    MissingMassiveApiKey,
    redact,
)


class _Resp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text or json.dumps(payload or {})

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": dict(params or {}), "headers": dict(headers or {})})
        if not self.responses:
            return _Resp(500, {"status": "ERROR"}, "empty")
        return self.responses.pop(0)


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    with pytest.raises(MissingMassiveApiKey):
        MassiveFuturesClient()


def test_redact_never_echoes_key():
    assert "secret-key" not in redact("Authorization: Bearer secret-key", "secret-key")
    assert "***REDACTED***" in redact("Authorization: Bearer secret-key", "secret-key")


def test_bearer_then_query_fallback(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "test-secret-key")
    session = _FakeSession(
        [
            _Resp(401, {"status": "NOT_AUTHORIZED"}, "nope"),
            _Resp(200, {"status": "OK", "results": [{"close": 1}]}, "ok"),
        ]
    )
    client = MassiveFuturesClient(session=session)
    probe = client.probe_auth(ticker="ESU6")
    assert probe.ok
    assert probe.style == "apiKey_query"
    assert client._auth["params"]["apiKey"] == "test-secret-key"
    # The probe record itself must not include the raw key.
    assert "test-secret-key" not in probe.detail


def test_all_auth_styles_rejected(monkeypatch):
    monkeypatch.setenv("MASSIVE_API_KEY", "test-secret-key")
    session = _FakeSession(
        [
            _Resp(401, {}, "a"),
            _Resp(401, {}, "b"),
            _Resp(403, {}, "c"),
            _Resp(401, {}, "d"),
        ]
    )
    client = MassiveFuturesClient(session=session)
    with pytest.raises(MassiveAuthError):
        client.probe_auth()
