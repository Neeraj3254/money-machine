from pathlib import Path
import requests
from research.market.upstox_client import UpstoxClient
INSTRUMENT = "NSE_EQ|INE002A01018"
VALID_PAYLOAD = {
    "status": "success",
    "data": {
        "NSE_EQ:TEST": {
            "instrument_token": INSTRUMENT,
            "last_price": 1234.5,
            "timestamp": "2026-10-19T09:20:00+05:30",
        }
    },
}
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
def test_valid_ltp_is_received_but_not_research_ready():
    session = FakeSession(FakeResponse(VALID_PAYLOAD))
    client = UpstoxClient(access_token="test-token", session=session)
    result = client.get_ltp(INSTRUMENT)
    assert result["status"] == "received_unvalidated"
    assert result["provider"] == "upstox"
    assert result["last_price"] == 1234.5
    assert result["source_available_timestamp"] is None
    assert result["research_ready"] is False
    assert result["trading_enabled"] is False
    assert result["local_receipt_timestamp"] > 0
    assert session.kwargs["params"] == {"instrument_key": INSTRUMENT}
    assert session.kwargs["headers"]["Authorization"] == "Bearer test-token"
    assert "test-token" not in repr(result)
def test_missing_token_fails_closed():
    client = UpstoxClient(access_token="", session=FakeSession(FakeResponse(VALID_PAYLOAD)))
    assert client.get_ltp(INSTRUMENT) == {
        "status": "not_configured",
        "reason": "missing_upstox_access_token",
    }
def test_blank_instrument_key_is_rejected():
    client = UpstoxClient(access_token="test-token")
    assert client.get_ltp(" ")["reason"] == "instrument_key_required"
def test_missing_instrument_quote_is_rejected():
    client = UpstoxClient(
        access_token="test-token",
        session=FakeSession(FakeResponse({"status": "success", "data": {}})),
    )
    assert client.get_ltp(INSTRUMENT)["reason"] == "expected_exactly_one_quote"
def test_invalid_last_prices_are_rejected():
    for value in ("bad", None, float("nan"), float("inf"), 0, -1):
        payload = {
            "status": "success",
            "data": {
                "NSE_EQ:TEST": {
                    "instrument_token": INSTRUMENT,
                    "last_price": value,
                }
            }
        }
        client = UpstoxClient(
            access_token="test-token",
            session=FakeSession(FakeResponse(payload)),
        )
        assert client.get_ltp(INSTRUMENT)["reason"] == "invalid_last_price"
def test_http_error_is_sanitized():
    session = FakeSession(
        FakeResponse(error=requests.HTTPError("private request details"))
    )
    client = UpstoxClient(access_token="secret-test-token", session=session)
    result = client.get_ltp(INSTRUMENT)
    assert result["status"] == "provider_error"
    assert result["reason"] == "HTTPError"
    assert "secret-test-token" not in repr(result)
    assert "private request details" not in repr(result)
def test_invalid_json_is_rejected():
    client = UpstoxClient(
        access_token="test-token",
        session=FakeSession(FakeResponse(ValueError("invalid JSON"))),
    )
    assert client.get_ltp(INSTRUMENT) == {
        "status": "invalid_response",
        "reason": "invalid_json",
    }
def test_token_can_be_read_from_env_file(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        'UPSTOX_ACCESS_TOKEN="example-local-token"\n',
        encoding="utf-8",
    )
    session = FakeSession(FakeResponse(VALID_PAYLOAD))
    client = UpstoxClient(session=session, env_path=env_file)
    result = client.get_ltp(INSTRUMENT)
    assert result["status"] == "received_unvalidated"
    assert session.kwargs["headers"]["Authorization"] == "Bearer example-local-token"
def test_nonpositive_timeout_is_rejected():
    try:
        UpstoxClient(access_token="test-token", timeout_seconds=0)
    except ValueError as exc:
        assert str(exc) == "timeout_seconds must be positive"
    else:
        raise AssertionError("Expected nonpositive timeout to be rejected")


def test_mismatched_provider_instrument_is_rejected():
    payload = {
        "status": "success",
        "data": {
            "NSE_EQ:TEST": {
                "instrument_token": "NSE_EQ|WRONG_INSTRUMENT",
                "last_price": 1234.5,
            }
        },
    }
    client = UpstoxClient(
        access_token="test-token",
        session=FakeSession(FakeResponse(payload)),
    )
    result = client.get_ltp(INSTRUMENT)
    assert result["status"] == "invalid_response"
    assert result["reason"] == "instrument_identity_mismatch"
    assert result["research_ready"] if "research_ready" in result else True
def test_receipt_timestamp_is_captured_after_ltp_response(monkeypatch):
    from types import SimpleNamespace
    from research.market import upstox_client as module
    started = 1_797_000_000.0
    completed = started + 2.0
    class TrackingSession(FakeSession):
        completed = False
        def get(self, url, **kwargs):
            response = super().get(url, **kwargs)
            self.completed = True
            return response
    session = TrackingSession(FakeResponse(VALID_PAYLOAD))
    monkeypatch.setattr(
        module,
        "time",
        SimpleNamespace(
            time=lambda: completed if session.completed else started
        ),
    )
    result = UpstoxClient(
        access_token="test-token",
        session=session,
    ).get_ltp(INSTRUMENT)
    assert result["status"] == "received_unvalidated"
    assert result["local_receipt_timestamp"] == completed
    assert result["source_available_timestamp"] is None
    assert result["research_ready"] is False
    assert result["trading_enabled"] is False
