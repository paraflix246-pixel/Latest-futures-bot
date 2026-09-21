"""Massive.com Futures REST client (Polygon rebrand).

Reads MASSIVE_API_KEY from the environment and never prints it.

Official Massive REST auth (docs/quickstart):

  1. Authorization: Bearer <key>   ← preferred for futures aggs
  2. ?apiKey=<key> query parameter
  3. Authorization: Bearer <key> plus ?apiKey=<key>
  4. X-API-KEY header

Futures aggregates:

  GET https://api.massive.com/futures/v1/aggs/{ticker}?resolution=5min&...

Confirmed tickers: MNQU5, MESU5, ESU5 (root + H/M/U/Z + 1-digit year).
`product_code` filters on /contracts have been flaky — enumerate HMUZ
contract months instead of relying on that filter.

Also: GET /futures/v1/contracts, GET /futures/v1/products
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

# CME equity-index quarterlies. product_code filters are flaky; enumerate.
HMUZ_MONTHS = ("H", "M", "U", "Z")


def enumerate_hmuz_tickers(root: str, start: str, end: str) -> List[str]:
    """Build MNQU5 / MESU5 / ESU5-style tickers, plus 2-digit-year aliases."""
    y0 = int(start[:4])
    y1 = int(end[:4])
    tickers: List[str] = []
    seen = set()
    for year in range(y0, y1 + 1):
        one = str(year)[-1]
        two = f"{year % 100:02d}"
        for month in HMUZ_MONTHS:
            for name in (f"{root}{month}{one}", f"{root}{month}{two}"):
                if name not in seen:
                    seen.add(name)
                    tickers.append(name)
    return tickers


DEFAULT_BASE = "https://api.massive.com"
AGGS_PATH = "/futures/v1/aggs/{ticker}"
CONTRACTS_PATH = "/futures/v1/contracts"
PRODUCTS_PATH = "/futures/v1/products"

# Do not log or interpolate the raw key. Redact any accidental leak.
_REDACT = "***REDACTED***"


class MissingMassiveApiKey(RuntimeError):
    """Raised when MASSIVE_API_KEY is unset or empty."""


class MassiveAuthError(RuntimeError):
    """Raised when every documented auth style is rejected."""


class MassiveApiError(RuntimeError):
    """Raised on a non-auth API failure after a working auth style is known."""


@dataclass
class AuthProbe:
    style: str
    status_code: int
    ok: bool
    detail: str


def _load_key() -> str:
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if not key:
        raise MissingMassiveApiKey(
            "MASSIVE_API_KEY is not set. Add it to the Cloud Agent / machine "
            "environment (never commit it). The Massive client and "
            "scripts/download_massive_futures.py read this env var only."
        )
    return key


def redact(text: str, key: str) -> str:
    if not key:
        return text
    return text.replace(key, _REDACT)


def _auth_attempts(key: str) -> List[Dict[str, Any]]:
    return [
        {"style": "bearer", "headers": {"Authorization": f"Bearer {key}"}, "params": {}},
        {"style": "apiKey_query", "headers": {}, "params": {"apiKey": key}},
        {
            "style": "bearer_plus_query",
            "headers": {"Authorization": f"Bearer {key}"},
            "params": {"apiKey": key},
        },
        {"style": "x_api_key", "headers": {"X-API-KEY": key}, "params": {}},
    ]


class MassiveFuturesClient:
    """Thin authenticated REST wrapper with pagination and auth fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE,
        timeout: float = 60.0,
        max_retries: int = 4,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._key = api_key if api_key is not None else _load_key()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self._auth: Optional[Dict[str, Any]] = None
        self.auth_probes: List[AuthProbe] = []

    def probe_auth(self, ticker: str = "ESU6") -> AuthProbe:
        """Try auth styles against a cheap aggregates request. Caches the first OK."""
        last_err: Optional[AuthProbe] = None
        for attempt in _auth_attempts(self._key):
            url = self.base_url + AGGS_PATH.format(ticker=ticker)
            params = {"resolution": "1session", "limit": 1, **attempt["params"]}
            headers = {
                "Accept": "application/json",
                "User-Agent": "latest-futures-bot-research/1.0",
                **attempt["headers"],
            }
            try:
                resp = self.session.get(url, params=params, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                probe = AuthProbe(attempt["style"], 0, False, redact(str(exc), self._key))
                self.auth_probes.append(probe)
                last_err = probe
                continue
            body = redact(resp.text[:300], self._key)
            ok = resp.status_code < 400
            probe = AuthProbe(attempt["style"], resp.status_code, ok, body)
            self.auth_probes.append(probe)
            if ok:
                self._auth = attempt
                return probe
            # 401/403: try the next style. Other codes still mean "auth reached the API".
            if resp.status_code not in (401, 403):
                # Non-auth failure (e.g. 404 ticker) still proves the style works.
                self._auth = attempt
                return AuthProbe(attempt["style"], resp.status_code, True, body)
            last_err = probe
        raise MassiveAuthError(
            "All Massive auth styles were rejected (Bearer / apiKey query / "
            f"X-API-KEY). Last status={getattr(last_err, 'status_code', None)}. "
            "Confirm MASSIVE_API_KEY is a valid Futures-plan key."
        )

    def _ensure_auth(self) -> Dict[str, Any]:
        if self._auth is None:
            self.probe_auth()
        assert self._auth is not None
        return self._auth

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        auth = self._ensure_auth()
        url = path if path.startswith("http") else self.base_url + path
        merged = dict(params or {})
        merged.update(auth["params"])
        headers = {
            "Accept": "application/json",
            "User-Agent": "latest-futures-bot-research/1.0",
            **auth["headers"],
        }
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                resp = self.session.get(url, params=merged, headers=headers, timeout=self.timeout)
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(min(2 ** attempt, 16))
                continue
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(min(2 ** attempt, 16))
                last_exc = MassiveApiError(f"HTTP {resp.status_code}")
                continue
            if resp.status_code in (401, 403):
                raise MassiveAuthError(
                    f"Massive rejected the cached auth style (HTTP {resp.status_code})."
                )
            if resp.status_code >= 400:
                raise MassiveApiError(
                    f"Massive HTTP {resp.status_code}: {redact(resp.text[:400], self._key)}"
                )
            payload = resp.json()
            if not isinstance(payload, dict):
                raise MassiveApiError("Massive response was not a JSON object")
            return payload
        raise MassiveApiError(f"Massive request failed after retries: {last_exc}")

    def _paginate(self, path: str, params: Optional[Dict[str, Any]] = None) -> Iterable[Dict[str, Any]]:
        payload = self._request(path, params)
        results = payload.get("results") or []
        for row in results:
            yield row
        next_url = payload.get("next_url")
        while next_url:
            # next_url is absolute; drop our extra query merge except auth.
            parsed = urlparse(next_url)
            q = dict(parse_qsl(parsed.query, keep_blank_values=True))
            # Strip any leaked key from the documented next_url and re-apply auth.
            q.pop("apiKey", None)
            q.pop("api_key", None)
            clean = urlunparse(parsed._replace(query=urlencode(q)))
            payload = self._request(clean, {})
            for row in payload.get("results") or []:
                yield row
            next_url = payload.get("next_url")

    def list_products(self, **filters: Any) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        return list(self._paginate(PRODUCTS_PATH, params))

    def list_contracts(
        self,
        product_code: Optional[str] = None,
        type_: str = "single",
        limit: int = 1000,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        params = {k: v for k, v in filters.items() if v is not None}
        if product_code:
            params["product_code"] = product_code
        if type_:
            params["type"] = type_
        params["limit"] = min(int(limit), 1000)
        return list(self._paginate(CONTRACTS_PATH, params))

    def list_aggregates(
        self,
        ticker: str,
        resolution: str = "5min",
        window_start_gte: Optional[str] = None,
        window_start_lte: Optional[str] = None,
        limit: int = 50000,
        sort: str = "window_start.asc",
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "resolution": resolution,
            "limit": min(int(limit), 50000),
            "sort": sort,
        }
        if window_start_gte:
            params["window_start.gte"] = window_start_gte
        if window_start_lte:
            params["window_start.lte"] = window_start_lte
        return list(self._paginate(AGGS_PATH.format(ticker=ticker), params))
