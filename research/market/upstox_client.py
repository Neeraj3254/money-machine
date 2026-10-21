"""Read-only Upstox LTP client; does not place orders or certify research readiness."""
from __future__ import annotations
import math
import os
import time
from pathlib import Path
from typing import Any
import requests
BASE_URL = "https://api.upstox.com/v3/market-quote/ltp"
def _read_access_token(env_path: Path | None = None) -> str | None:
    """Read the token from the environment or a local .env without printing it."""
    value = os.environ.get("UPSTOX_ACCESS_TOKEN")
    if value and value.strip():
        return value.strip().strip("\"'")
    path = env_path or Path.cwd() / ".env"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        candidate = line.strip()
        if not candidate or candidate.startswith("#"):
            continue
        if candidate.startswith("export "):
            candidate = candidate[7:].lstrip()
        if candidate.startswith("UPSTOX_ACCESS_TOKEN="):
            value = candidate.split("=", 1)[1].strip().strip("\"'")
            return value or None
    return None
class UpstoxClient:
    """Fetch one LTP response. Successful responses remain unvalidated research data."""
    def __init__(
        self,
        access_token: str | None = None,
        *,
        timeout_seconds: float = 8.0,
        session: Any = None,
        env_path: Path | None = None,
    ) -> None:
        token = (
            access_token.strip()
            if access_token is not None
            else _read_access_token(env_path)
        )
        self._access_token = token.strip() if token and token.strip() else None
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self._session = session if session is not None else requests.Session()
    def get_ltp(self, instrument_key: str) -> dict[str, Any]:
        """Return one LTP without inventing publication timestamps or readiness."""
        if not isinstance(instrument_key, str) or not instrument_key.strip():
            return {"status": "invalid_request", "reason": "instrument_key_required"}
        instrument_key = instrument_key.strip()
        if not self._access_token:
            return {
                "status": "not_configured",
                "reason": "missing_upstox_access_token",
            }
        received_at = None
        try:
            response = self._session.get(
                BASE_URL,
                params={"instrument_key": instrument_key},
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            received_at = time.time()
        except requests.RequestException as exc:
            return {"status": "provider_error", "reason": type(exc).__name__}
        except (ValueError, TypeError):
            return {"status": "invalid_response", "reason": "invalid_json"}
        if not isinstance(payload, dict):
            return {"status": "invalid_response", "reason": "expected_object"}
        data = payload.get("data")
        if not isinstance(data, dict):
            return {"status": "invalid_response", "reason": "missing_data_object"}
        if payload.get("status") != "success":
            return {"status": "invalid_response", "reason": "provider_status_not_success"}
        if len(data) != 1:
            return {
                "status": "invalid_response",
                "reason": "expected_exactly_one_quote",
            }
        response_key, quote = next(iter(data.items()))
        if not isinstance(quote, dict):
            return {
                "status": "invalid_response",
                "reason": "instrument_quote_missing",
            }
        provider_instrument_token = quote.get("instrument_token")
        if (
            not isinstance(provider_instrument_token, str)
            or provider_instrument_token != instrument_key
        ):
            return {
                "status": "invalid_response",
                "reason": "instrument_identity_mismatch",
            }
        try:
            last_price = float(quote["last_price"])
            if not math.isfinite(last_price) or last_price <= 0:
                raise ValueError("invalid price")
        except (KeyError, ValueError, TypeError, OverflowError):
            return {"status": "invalid_response", "reason": "invalid_last_price"}
        return {
            "status": "received_unvalidated",
            "provider": "upstox",
            "instrument_key": instrument_key,
            "provider_response_key": response_key,
            "provider_instrument_token": provider_instrument_token,
            "last_price": last_price,
            "provider_timestamp_raw": quote.get("timestamp"),
            "local_receipt_timestamp": received_at,
            "source_available_timestamp": None,
            "research_ready": False,
            "trading_enabled": False,
        }


