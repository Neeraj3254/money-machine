from datetime import datetime, timezone
import requests
from research.market.upstox_options_client import (
    OPTION_CHAIN_URL,
    UpstoxOptionsClient,
)
class FakeResponse:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
    def raise_for_status(self):
        if self.error:
            raise self.error
    def json(self):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload
class FakeSession:
    def __init__(self, response):
        self.response = response
        self.kwargs = None
    def get(self, url, **kwargs):
        self.kwargs = {"url": url, **kwargs}
        return self.response
def valid_payload():
    return {
        "status": "success",
        "data": [{
            "expiry": "2026-10-29",
            "strike_price": 25000,
            "underlying_key": "NSE_INDEX|Nifty 50",
            "underlying_spot_price": 25010.0,
            "pcr": 1.05,
            "call_options": {
                "instrument_key": "NSE_FO|CALLTEST",
                "market_data": {
                    "ltp": 100.0, "bid_price": 99.5, "ask_price": 100.5,
                    "bid_qty": 20, "ask_qty": 25, "volume": 1000, "oi": 5000,
                },
                "option_greeks": {"delta": 0.5, "iv": 18.0},
            },
            "put_options": {
                "instrument_key": "NSE_FO|PUTTEST",
                "market_data": {
                    "ltp": 95.0, "bid_price": 94.5, "ask_price": 95.5,
                    "bid_qty": 22, "ask_qty": 24, "volume": 900, "oi": 4800,
                },
                "option_greeks": {"delta": -0.5, "iv": 19.0},
            },
        }],
    }
def test_valid_chain_is_received_but_not_research_ready():
    session = FakeSession(FakeResponse(valid_payload()))
    client = UpstoxOptionsClient(access_token="test-token", session=session)
    result = client.get_option_chain("NSE_INDEX|Nifty 50", "2026-10-29")
    assert result["status"] == "received_unvalidated"
    assert result["contract_count"] == 1
    assert result["contracts"][0]["call_options"]["market_data"]["ask_price"] == 100.5
    assert result["contracts"][0]["put_options"]["option_greeks"]["delta"] == -0.5
    assert result["source_available_timestamp"] is None
    assert result["research_ready"] is False
    assert result["trading_enabled"] is False
    assert session.kwargs["url"] == OPTION_CHAIN_URL
    assert session.kwargs["params"] == {
        "instrument_key": "NSE_INDEX|Nifty 50",
        "expiry_date": "2026-10-29",
    }
    assert session.kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert "test-token" not in repr(result)
def test_missing_token_fails_closed():
    result = UpstoxOptionsClient(access_token="").get_option_chain(
        "NSE_INDEX|Nifty 50", "2026-10-29"
    )
    assert result == {
        "status": "not_configured",
        "reason": "missing_upstox_access_token",
    }
def test_invalid_request_is_rejected():
    client = UpstoxOptionsClient(access_token="test-token")
    assert client.get_option_chain("", "2026-10-29")["reason"] == "instrument_key_required"
    assert client.get_option_chain("NSE_INDEX|Nifty 50", "not-a-date")["status"] == "invalid_request"
def test_wrong_underlying_is_rejected():
    payload = valid_payload()
    payload["data"][0]["underlying_key"] = "NSE_INDEX|Wrong"
    result = UpstoxOptionsClient(
        access_token="test-token",
        session=FakeSession(FakeResponse(payload)),
    ).get_option_chain("NSE_INDEX|Nifty 50", "2026-10-29")
    assert result["reason"] == "underlying_identity_mismatch"
def test_http_error_is_sanitized():
    client = UpstoxOptionsClient(
        access_token="secret-test-token",
        session=FakeSession(FakeResponse(error=requests.HTTPError("private details"))),
    )
    result = client.get_option_chain("NSE_INDEX|Nifty 50", "2026-10-29")
    assert result == {"status": "provider_error", "reason": "HTTPError"}
    assert "secret-test-token" not in repr(result)
    assert "private details" not in repr(result)
def test_empty_chain_is_rejected():
    result = UpstoxOptionsClient(
        access_token="test-token",
        session=FakeSession(FakeResponse({"status": "success", "data": []})),
    ).get_option_chain("NSE_INDEX|Nifty 50", "2026-10-29")
    assert result["reason"] == "missing_or_empty_chain"
def test_invalid_json_is_rejected():
    result = UpstoxOptionsClient(
        access_token="test-token",
        session=FakeSession(FakeResponse(ValueError("bad json"))),
    ).get_option_chain("NSE_INDEX|Nifty 50", "2026-10-29")
    assert result == {"status": "invalid_response", "reason": "invalid_json"}
def test_receipt_timestamp_is_captured_after_option_chain_response(monkeypatch):
    from research.market import upstox_options_client as module
    started = datetime(2026, 10, 20, 3, 0, tzinfo=timezone.utc)
    completed = datetime(2026, 10, 20, 3, 0, 2, tzinfo=timezone.utc)
    class TrackingSession(FakeSession):
        completed = False
        def get(self, url, **kwargs):
            response = super().get(url, **kwargs)
            self.completed = True
            return response
    session = TrackingSession(FakeResponse(valid_payload()))
    class FakeClock:
        @staticmethod
        def now(tz=None):
            return completed if session.completed else started
    monkeypatch.setattr(module, "datetime", FakeClock)
    result = UpstoxOptionsClient(
        access_token="test-token",
        session=session,
    ).get_option_chain("NSE_INDEX|Nifty 50", "2026-10-29")
    assert result["status"] == "received_unvalidated"
    assert result["local_receipt_timestamp"] == completed.isoformat()
    assert result["source_available_timestamp"] is None
    assert result["research_ready"] is False
    assert result["trading_enabled"] is False
