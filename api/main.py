from fastapi import FastAPI

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