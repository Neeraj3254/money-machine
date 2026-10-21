import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_legacy_analyze_route_cannot_bypass_unified_evidence_gates(client):
    response = client.post("/analyze", params={"asset": "TCS", "capital": 13000,
                                               "horizon_days": 1, "max_loss_percent": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "NO TRADE"
    assert body["reason"] == "LEGACY_SCAN_RETIRED_FOR_UNIFIED_EVIDENCE_GATES"
    assert body["universe"]["scan_status"] == "NOT_RUN"
    assert body["execution"]["automatic_execution"] is False


def test_legacy_options_request_remains_no_trade(client):
    response = client.post("/analyze", params={"asset": "SENSEX CALL", "capital": 13000,
                                               "horizon_days": 1, "max_loss_percent": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "NO TRADE"
    assert body["reason"] == "OPTIONS_VALIDATION_PIPELINE_UNAVAILABLE"
    assert body["execution"]["automatic_execution"] is False


def test_versioned_api_route_reports_missing_data_as_no_trade(client):
    response = client.post("/v1/research/analyze", json={"schema_version": "research-analysis-request-v1",
                                                          "symbol": "TCS", "as_of_date": "2025-01-02",
                                                          "horizon_days": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "NO_TRADE"
    assert body["stages"]["market_data"]["reason"] == "dataset_not_attached"


def test_versioned_api_route_validates_request(client):
    response = client.post("/v1/research/analyze", json={"symbol": " TCS", "as_of_date": "bad",
                                                          "horizon_days": 0})
    assert response.status_code == 422
