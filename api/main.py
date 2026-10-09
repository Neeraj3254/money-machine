import math

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from research.market.live_premove import build_live_premove_snapshot


app = FastAPI(
    title="Money Machine API",
    version="0.3.0",
)


class AnalyzeRequest(BaseModel):
    asset: str
    capital: float
    horizon_days: int
    max_loss_percent: float


@app.get("/")
def root():
    return {
        "system": "Money Machine",
        "status": "online",
        "version": "0.3.0",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    if request.capital <= 0:
        raise HTTPException(
            status_code=400,
            detail="capital must be positive",
        )

    if request.horizon_days <= 0:
        raise HTTPException(
            status_code=400,
            detail="horizon_days must be positive",
        )

    if request.max_loss_percent <= 0:
        raise HTTPException(
            status_code=400,
            detail="max_loss_percent must be positive",
        )

    return {
        "system": "Money Machine",
        "analysis_status": "research_only",
        "asset": request.asset.upper(),
        "capital": request.capital,
        "horizon_days": request.horizon_days,
        "max_loss_percent": request.max_loss_percent,
        "decision": "NO TRADE",
        "reason": "No validated market model is currently active.",
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
        # Build the snapshot before reading its columns or attributes.
        snapshot = build_live_premove_snapshot(top_n=top_n)

    except Exception as exc:
        # Return a controlled error rather than an unexplained server crash.
        raise HTTPException(
            status_code=503,
            detail={
                "message": "EOD research data is temporarily unavailable.",
                "error_type": type(exc).__name__,
                "note": (
                    "No candidate ranking is available for this request. "
                    "Retry later or investigate the data provider."
                ),
            },
        ) from exc

    if snapshot is None or snapshot.empty:
        raise HTTPException(
            status_code=503,
            detail="The data provider returned no usable candidate data.",
        )

    scan_diagnostics = {
        "requested_symbols": snapshot.attrs.get("requested_symbols"),
        "symbols_with_data": snapshot.attrs.get("symbols_with_data"),
        "symbols_without_valid_data": snapshot.attrs.get(
            "symbols_without_valid_data", []
        ),
        "benchmark": snapshot.attrs.get("benchmark"),
        "data_source": snapshot.attrs.get("data_source"),
    }

    columns = [
        "SYMBOL", "ISIN", "TRADE_DATE", "CLSPRIC",
        "Setup_Score", "Chase_Risk", "Adjusted_Setup_Score",
        "PreMove_Status", "PreMove_Rank",
        "RVOL_5D", "RVOL_10D", "RVOL_20D", "RVOL_50D",
        "ATR_Expansion", "Range_Expansion",
        "Breakout_5D", "Breakout_10D", "Breakout_20D",
        "Breakout_50D", "Breakout_52W",
        "VWAP_Relation", "EMA_Stack_Bullish",
        "RSI_14", "MACD", "MACD_Signal",
        "Momentum_1D", "Momentum_3D", "Momentum_5D",
        "Momentum_10D", "Momentum_20D",
        "Relative_Strength_NIFTY_1D",
        "Relative_Strength_NIFTY_3D",
        "Relative_Strength_NIFTY_5D",
        "Relative_Strength_NIFTY_10D",
        "Volume_Acceleration_1D",
        "Gap_Pct", "Pullback_Depth_20D",
        "Distance_From_20D_High",
        "Liquidity_Turnover",
        "CATALYST_SCORE", "CATALYST_STATUS",
    ]

    available = [
        column for column in columns
        if column in snapshot.columns
    ]

    clean = snapshot[available].copy()

    if "SYMBOL" not in clean.columns:
        raise HTTPException(
            status_code=503,
            detail="The scanner output is missing the required SYMBOL column.",
        )

    # Normalize dates and non-finite numbers for JSON serialization.
    if "TRADE_DATE" in clean.columns:
        clean["TRADE_DATE"] = clean["TRADE_DATE"].map(
            lambda value: (
                value.isoformat()
                if hasattr(value, "isoformat")
                else value
            )
        )

    numeric_exclusions = {
        "SYMBOL", "ISIN", "TRADE_DATE", "Detector_Status","PreMove_Status",
        "Breakout_5D", "Breakout_10D", "Breakout_20D",
        "Breakout_50D", "Breakout_52W", "VWAP_Relation",
        "EMA_Stack_Bullish", "CATALYST_STATUS",
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

        # Count nulls and non-null values that cannot be parsed numerically.
        missing_numeric_cells += int(original.isna().sum())
        missing_numeric_cells += int(
            (original.notna() & values.isna()).sum()
        )

        finite_mask = values.map(
            lambda value: (
                pd.isna(value) or math.isfinite(float(value))
            )
        )
        non_finite_cells += int((~finite_mask).sum())

        # Replace infinity and invalid numeric values with JSON-safe nulls.
        clean[column] = values.map(
            lambda value: (
                None
                if pd.isna(value) or not math.isfinite(float(value))
                else float(value)
            )
        )

    candidate_records = clean.to_dict(orient="records")

    unique_symbols = {
        str(row["SYMBOL"])
        for row in candidate_records
        if row.get("SYMBOL") is not None
    }

    data_quality = {
        "requested_top_n": top_n,
        "returned_candidates": len(candidate_records),
        "unique_symbols": len(unique_symbols),
        "duplicate_symbol_rows": (
            len(candidate_records) - len(unique_symbols)
        ),
        "missing_numeric_cells": missing_numeric_cells,
        "non_finite_numeric_cells": non_finite_cells,
        "response_audit_scope": "returned_candidates_only",
        "warning": (
            "This audit does not establish full-universe download "
            "completeness or predictive validity."
        ),
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
            "Intraday VWAP and news/catalyst evidence are not "
            "fabricated; no automatic execution."
        ),
        "candidates": candidate_records,
        "data_quality": data_quality,
        "scan_diagnostics": scan_diagnostics,
    }

    # Reject any unexpected NaN or infinity that remains in the response.
    return JSONResponse(
        content=response,
        status_code=200,
    )
