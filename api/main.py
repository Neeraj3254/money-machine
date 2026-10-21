
import math
import os
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from research.orchestration import run_research_analysis
from research.market.upstox_client import UpstoxClient


app = FastAPI(
    title="Money Machine API",
    version="0.2.0",
    description=(
        "Evidence-first market research API. "
        "Research candidates are not trade recommendations or execution orders."
    ),
)


def make_json_safe(value: Any) -> Any:
    """Convert common Python, NumPy and pandas values into JSON-safe values."""
    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(item) for item in value]

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    if isinstance(value, np.ndarray):
        return make_json_safe(value.tolist())

    if isinstance(value, np.generic):
        value = value.item()

    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None

    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value)

    if isinstance(value, (bool, np.bool_)):
        return bool(value)

    if isinstance(value, pd.DataFrame):
        return make_json_safe(value.to_dict(orient="records"))

    if isinstance(value, pd.Series):
        return make_json_safe(value.to_dict())

    if value is pd.NA or value is pd.NaT:
        return None

    try:
        missing = pd.isna(value)
        if isinstance(missing, (bool, np.bool_)) and missing:
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)



@app.get("/v1/market-data/ltp")
def upstox_ltp(
    instrument_key: str = Query(
        default="NSE_EQ|INE002A01018", min_length=1, max_length=100
    ),
):
    """Opt-in, read-only quote proxy. Quotes remain unvalidated."""
    if os.environ.get("MONEY_MACHINE_ENABLE_UPSTOX_QUOTE_API") != "1":
        raise HTTPException(status_code=404, detail="quote_endpoint_disabled")
    result = UpstoxClient(timeout_seconds=8.0).get_ltp(instrument_key)
    status = result.get("status")
    if status == "not_configured":
        raise HTTPException(status_code=503, detail=result)
    if status == "invalid_request":
        raise HTTPException(status_code=422, detail=result)
    if status in {"provider_error", "invalid_response"}:
        raise HTTPException(status_code=502, detail=result)
    if status != "received_unvalidated":
        raise HTTPException(status_code=502, detail={"status": "unexpected_client_result"})
    return make_json_safe({
        "schema_version": "market-quote-response-v1",
        "data_status": "received_unvalidated",
        "research_ready": False,
        "trading_enabled": False,
        "quote": result,
    })
@app.get("/")
def root():
    return {
        "system": "Money Machine",
        "status": "online",
        "version": "0.2.0",
        "automatic_execution": False,
    }


@app.get("/health")
def health():
    # Process health only; this does not certify market-data freshness.
    return {
        "status": "healthy",
        "market_data_validated": False,
        "automatic_execution": False,
    }


@app.get("/v1/research/readiness")
def research_readiness():
    """Process/API status is separate from dataset or strategy readiness."""
    return {
        "schema_version": "research-readiness-response-v1",
        "api_status": "healthy",
        "research_data_status": "NOT_ATTACHED",
        "decision": "NO_TRADE",
        "automatic_execution": False,
    }


@app.post("/v1/research/analyze")
def research_analyze(payload: dict[str, Any]):
    """Versioned fail-closed orchestration endpoint; currently no dataset loader is configured."""
    try:
        result = run_research_analysis(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc)}) from exc
    return make_json_safe(result)


@app.get("/premove-scan")
def premove_scan(
    top_n: int = Query(default=25, ge=1, le=100),
):
    """Fail closed until an authorized, provenance-bound feed is configured."""
    raise HTTPException(
        status_code=503,
        detail={
            "status": "DATA_UNAVAILABLE",
            "decision": "NO_TRADE",
            "reason": "live_feed_not_configured_or_verified",
            "requested_top_n": top_n,
            "automatic_execution": False,
        },
    )


@app.post("/analyze")
def analyze(
    asset: str = Query(..., min_length=1),
    capital: float = Query(..., gt=0, allow_inf_nan=False),
    horizon_days: int = Query(..., gt=0),
    max_loss_percent: float = Query(
        ...,
        gt=0,
        le=100,
        allow_inf_nan=False,
    ),
):
    """
    Compatibility endpoint retired; use the versioned evidence-gated route.
    """
    normalized_asset = asset.strip().upper()

    if not normalized_asset:
        raise HTTPException(
            status_code=422,
            detail="asset must not be blank",
        )

    # Retire the legacy scanner path: it has no source-readiness, timing, or
    # provenance binding. The versioned route below the same service is the
    # only path that may produce a research proposal, and it is fail-closed
    # until a configured dataset resolver supplies verified evidence.
    options_assets = {"NIFTY CALL", "NIFTY PUT", "SENSEX CALL", "SENSEX PUT"}
    return {
        "system": "Money Machine",
        "request": {"asset": normalized_asset, "capital": capital,
                    "horizon_days": horizon_days, "max_loss_percent": max_loss_percent},
        "decision": "NO TRADE",
        "reason": "OPTIONS_VALIDATION_PIPELINE_UNAVAILABLE" if normalized_asset in options_assets else "LEGACY_SCAN_RETIRED_FOR_UNIFIED_EVIDENCE_GATES",
        "universe": {"scan_status": "NOT_RUN", "stocks_scanned": 0,
                     "successful_scans": 0, "scan_errors": 0,
                     "validated_candidates": 0, "results": []},
        "execution": {"human_approval_required": True, "automatic_execution": False},
    }
