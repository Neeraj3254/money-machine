import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
import api.main as api
def test_premove_scan_serializes_non_finite_values(monkeypatch):
    mock = pd.DataFrame([
        {
            "SYMBOL": "TESTA",
            "TRADE_DATE": pd.Timestamp("2026-10-08"),
            "CLSPRIC": 100.0,
            "Setup_Score": 8.0,
            "Gap_Pct": np.nan,
        },
        {
            "SYMBOL": "TESTA",
            "TRADE_DATE": pd.Timestamp("2026-10-08"),
            "CLSPRIC": 100.0,
            "Setup_Score": np.inf,
            "Gap_Pct": "invalid",
        },
    ])
    mock.attrs.update({
        "requested_symbols": 50,
        "symbols_with_data": 1,
        "symbols_without_valid_data": [],
        "benchmark": "MOCK_INDEX",
        "data_source": "MOCK_ONLY",
    })
    monkeypatch.setattr(
        api,
        "build_live_premove_snapshot",
        lambda **kwargs: mock.copy(),
    )
    response = TestClient(api.app).get("/premove-scan?top_n=2")
    assert response.status_code == 200
    body = response.json()
    assert len(body["candidates"]) == 2
    assert body["candidates"][0]["Gap_Pct"] is None
    assert body["candidates"][1]["Setup_Score"] is None
    assert body["data_quality"]["unique_symbols"] == 1
    assert body["data_quality"]["duplicate_symbol_rows"] == 1
    assert body["data_quality"]["non_finite_numeric_cells"] >= 1
    assert body["scan_diagnostics"]["benchmark"] == "MOCK_INDEX"
