"""Read-only Upstox option-chain retrieval; never certifies trading readiness."""
from __future__ import annotations
from datetime import date, datetime, timezone
import math
from typing import Any
import requests
from .upstox_client import _read_access_token
OPTION_CHAIN_URL = "https://api.upstox.com/v2/option/chain"
RELATIVE_EXPIRIES = {
    "current_week", "next_week", "far_week",
    "current_month", "next_month", "far_month",
}
class UpstoxOptionsClient:
    """Fetch an option chain as unvalidated research data only."""
    def __init__(
        self,
        access_token: str | None = None,
        *,
        timeout_seconds: float = 8.0,
        session: Any = None,
        env_path=None,
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
    def get_option_chain(
        self, instrument_key: str, expiry_date: str
    ) -> dict[str, Any]:
        if not isinstance(instrument_key, str) or not instrument_key.strip():
            return {"status": "invalid_request", "reason": "instrument_key_required"}
        if not isinstance(expiry_date, str) or not expiry_date.strip():
            return {"status": "invalid_request", "reason": "expiry_date_required"}
        instrument_key = instrument_key.strip()
        expiry_date = expiry_date.strip()
        if expiry_date not in RELATIVE_EXPIRIES:
            try:
                if date.fromisoformat(expiry_date).isoformat() != expiry_date:
                    raise ValueError
            except ValueError:
                return {
                    "status": "invalid_request",
                    "reason": "expiry_date_must_be_iso_date_or_supported_keyword",
                }
        if not self._access_token:
            return {
                "status": "not_configured",
                "reason": "missing_upstox_access_token",
            }
        received_at = None
        try:
            response = self._session.get(
                OPTION_CHAIN_URL,
                params={
                    "instrument_key": instrument_key,
                    "expiry_date": expiry_date,
                },
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self._access_token}",
                },
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            received_at = datetime.now(timezone.utc).isoformat()
        except requests.RequestException as exc:
            return {"status": "provider_error", "reason": type(exc).__name__}
        except (ValueError, TypeError):
            return {"status": "invalid_response", "reason": "invalid_json"}
        if not isinstance(payload, dict):
            return {"status": "invalid_response", "reason": "expected_object"}
        if payload.get("status") != "success":
            return {"status": "invalid_response", "reason": "provider_status_not_success"}
        rows = payload.get("data")
        if not isinstance(rows, list) or not rows:
            return {"status": "invalid_response", "reason": "missing_or_empty_chain"}
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                return {"status": "invalid_response", "reason": "invalid_chain_row"}
            if row.get("underlying_key") != instrument_key:
                return {"status": "invalid_response", "reason": "underlying_identity_mismatch"}
            expiry = row.get("expiry")
            if not isinstance(expiry, str):
                return {"status": "invalid_response", "reason": "missing_contract_expiry"}
            try:
                actual_expiry = date.fromisoformat(expiry)
            except ValueError:
                return {"status": "invalid_response", "reason": "invalid_contract_expiry"}
            if expiry_date not in RELATIVE_EXPIRIES and expiry != expiry_date:
                return {"status": "invalid_response", "reason": "contract_expiry_mismatch"}
            strike = row.get("strike_price")
            spot = row.get("underlying_spot_price")
            if (
                isinstance(strike, bool) or not isinstance(strike, (int, float))
                or not math.isfinite(strike) or strike <= 0
            ):
                return {"status": "invalid_response", "reason": "invalid_strike_price"}
            if (
                isinstance(spot, bool) or not isinstance(spot, (int, float))
                or not math.isfinite(spot) or spot <= 0
            ):
                return {"status": "invalid_response", "reason": "invalid_underlying_spot"}
            clean_sides = {}
            for side in ("call_options", "put_options"):
                option = row.get(side)
                if option is None:
                    clean_sides[side] = None
                    continue
                if not isinstance(option, dict):
                    return {"status": "invalid_response", "reason": "invalid_option_side"}
                key = option.get("instrument_key")
                market = option.get("market_data")
                greeks = option.get("option_greeks", {})
                if not isinstance(key, str) or not key.strip():
                    return {"status": "invalid_response", "reason": "missing_option_instrument_key"}
                if not isinstance(market, dict):
                    return {"status": "invalid_response", "reason": "missing_option_market_data"}
                if greeks is not None and not isinstance(greeks, dict):
                    return {"status": "invalid_response", "reason": "invalid_option_greeks"}
                clean_sides[side] = {
                    "instrument_key": key,
                    "market_data": market,
                    "option_greeks": greeks or {},
                }
            if clean_sides["call_options"] is None and clean_sides["put_options"] is None:
                return {"status": "invalid_response", "reason": "row_has_no_option_sides"}
            normalized.append({
                "expiry": actual_expiry.isoformat(),
                "strike_price": float(strike),
                "underlying_key": instrument_key,
                "underlying_spot_price": float(spot),
                "pcr": row.get("pcr"),
                **clean_sides,
            })
        return {
            "status": "received_unvalidated",
            "provider": "upstox",
            "underlying_key": instrument_key,
            "requested_expiry": expiry_date,
            "local_receipt_timestamp": received_at,
            "source_available_timestamp": None,
            "contract_count": len(normalized),
            "contracts": normalized,
            "research_ready": False,
            "trading_enabled": False,
        }
