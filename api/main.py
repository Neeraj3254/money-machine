import math
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from research.market.live_premove import build_live_premove_snapshot

from research.v2_engine.hypotheses import get_hypothesis
from research.v2_engine.features import build_trend_strength
from research.v2_engine.outcomes import add_forward_return
from research.v2_engine.scanner import scan_universe
from research.v2_engine.validation import validate_experiment
from research.v2_engine.runner import run_dataframe_experiment
from research.v2_engine.stability import (
    evaluate_time_stability,
    summarize_time_stability,
)
from research.v2_engine.oos import (
    split_train_test,
    evaluate_oos,
)

import pandas as pd


app = FastAPI(
    title="Money Machine API",
    version="0.2.0",
)


@app.get("/")
def root():
    return {
        "system": "Money Machine",
        "status": "online",
        "version": "0.2.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }



@app.get("/premove-scan")
def premove_scan(top_n: int = 25):
    """Return EOD research candidates; never execute trades."""
    if top_n < 1 or top_n > 100:
        raise HTTPException(
            status_code=400,
            detail="top_n must be between 1 and 100",
        )
    try:
        snapshot = build_live_premove_snapshot(top_n=top_n)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "EOD research data is temporarily unavailable.",
                "error_type": type(exc).__name__,
                "note": "No candidate ranking is available for this request.",
            },
        ) from exc
    if snapshot is None or snapshot.empty:
        raise HTTPException(
            status_code=503,
            detail="The data provider returned no usable candidate data.",
        )
    columns = [
        "SYMBOL", "ISIN", "TRADE_DATE", "CLSPRIC",
        "Setup_Score", "Chase_Risk", "Adjusted_Setup_Score",
        "PreMove_Status", "PreMove_Rank",
        "RVOL_5D", "RVOL_10D", "RVOL_20D", "RVOL_50D",
        "Volume_Acceleration_1D", "Return_1D", "Gap_Pct",
        "ATR_Range_Ratio", "Near_20D_High", "Pullback_Depth_20D",
        "Distance_From_20D_High", "Liquidity_Turnover",
        "CATALYST_SCORE", "CATALYST_STATUS",
    ]
    available = [column for column in columns if column in snapshot.columns]
    clean = snapshot[available].copy()
    if "SYMBOL" not in clean.columns:
        raise HTTPException(
            status_code=503,
            detail="The scanner output is missing the required SYMBOL column.",
        )
    if "TRADE_DATE" in clean.columns:
        clean["TRADE_DATE"] = clean["TRADE_DATE"].map(
            lambda value: value.isoformat()
            if hasattr(value, "isoformat") else value
        )
    numeric_exclusions = {
        "SYMBOL", "ISIN", "TRADE_DATE", "Detector_Status",
        "PreMove_Status", "Breakout_5D", "Breakout_10D",
        "Breakout_20D", "Breakout_50D", "Breakout_52W",
        "VWAP_Relation", "EMA_Stack_Bullish", "CATALYST_STATUS",
    }
    numeric_columns = [
        column for column in clean.columns
        if column not in numeric_exclusions
    ]
    missing_numeric_cells = 0
    non_finite_cells = 0
    for column in numeric_columns:
        original = clean[column]
        values = pd.to_numeric(original, errors="coerce")
        missing_numeric_cells += int(original.isna().sum())
        missing_numeric_cells += int(
            (original.notna() & values.isna()).sum()
        )
        finite_mask = values.map(
            lambda value: pd.isna(value) or math.isfinite(float(value))
        )
        non_finite_cells += int((~finite_mask).sum())
        clean[column] = values.map(
            lambda value: None
            if pd.isna(value) or not math.isfinite(float(value))
            else float(value)
        )
    candidate_records = clean.to_dict(orient="records")
    def make_json_safe(value):
        if isinstance(value, dict):
            return {key: make_json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [make_json_safe(item) for item in value]
        if value is None:
            return None
        if hasattr(value, "item"):
            value = value.item()
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        if pd.isna(value):
            return None
        return value
    candidate_records = make_json_safe(candidate_records)
    unique_symbols = {
        str(row["SYMBOL"])
        for row in candidate_records
        if row.get("SYMBOL") is not None
    }
    response = {
        "system": "Money Machine",
        "module": "PreMovePatternDetector",
        "status": "RESEARCH_CANDIDATE_ONLY",
        "data_source": (
            "Yahoo Finance EOD via yfinance; research fallback, "
            "not official NSE intraday data"
        ),
        "data_note": (
            "Intraday VWAP and news/catalyst evidence are not fabricated; "
            "no automatic execution."
        ),
        "candidates": candidate_records,
        "data_quality": {
            "requested_top_n": top_n,
            "returned_candidates": len(candidate_records),
            "unique_symbols": len(unique_symbols),
            "duplicate_symbol_rows": len(candidate_records) - len(unique_symbols),
            "missing_numeric_cells": missing_numeric_cells,
            "non_finite_numeric_cells": non_finite_cells,
            "response_audit_scope": "returned_candidates_only",
            "warning": (
                "This audit does not establish full-universe download "
                "completeness or predictive validity."
            ),
        },

        "scan_diagnostics": {
            "requested_symbols": snapshot.attrs.get("requested_symbols"),
            "symbols_with_data": snapshot.attrs.get("symbols_with_data"),
            "symbols_without_valid_data": snapshot.attrs.get(
                "symbols_without_valid_data", []
            ),
            "benchmark": snapshot.attrs.get("benchmark"),
            "data_source": snapshot.attrs.get("data_source"),
            "relative_strength_evidence": snapshot.attrs.get(
                "relative_strength_evidence", "unavailable"
            ),
            "missing_relative_strength_count": snapshot.attrs.get(
                "missing_relative_strength_count"
            ),
        },

    }
    return JSONResponse(content=response, status_code=200)
@app.post("/analyze")
def analyze(
    asset: str,
    capital: float,
    horizon_days: int,
    max_loss_percent: float,
):
    if capital <= 0:
        raise ValueError("capital must be positive")

    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")

    if max_loss_percent <= 0:
        raise ValueError("max_loss_percent must be positive")

    # ---------------------------------------------------------
    # 1. SCAN THE RESEARCH UNIVERSE
    # ---------------------------------------------------------

    universe_results = scan_universe(
        cost_per_trade=0.001,
    )

    # ---------------------------------------------------------
    # 2. IDENTIFY VALIDATED CANDIDATES
    # ---------------------------------------------------------

    validated_candidates = [
        result
        for result in universe_results
        if result.get("validation_status") == "VALIDATED_RESEARCH_EDGE"
    ]

    # ---------------------------------------------------------
    # 3. DECISION
    # ---------------------------------------------------------

    if not validated_candidates:
        decision = "NO TRADE"
    else:
        decision = "RESEARCH CANDIDATE"

    # ---------------------------------------------------------
    # 4. RISK
    # ---------------------------------------------------------

    maximum_loss_rupees = (
        capital * max_loss_percent / 100
    )

    # ---------------------------------------------------------
    # 5. RESPONSE
    # ---------------------------------------------------------

    return {
        "system": "Money Machine",

        "request": {
            "asset": asset.upper(),
            "capital": capital,
            "horizon_days": horizon_days,
            "max_loss_percent": max_loss_percent,
        },

        "decision": decision,

        "universe": {
            "stocks_scanned": len(universe_results),
            "validated_candidates": len(validated_candidates),
            "results": universe_results,
        },

        "risk": {
            "capital": capital,
            "max_loss_percent": max_loss_percent,
            "maximum_loss_rupees": maximum_loss_rupees,
        },

        "execution": {
            "human_approval_required": True,
            "automatic_execution": False,
        },
    }
