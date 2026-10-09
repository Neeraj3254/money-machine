from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd

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
        raise ValueError("capital must be positive")
    if request.horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    if request.max_loss_percent <= 0:
        raise ValueError("max_loss_percent must be positive")

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
    """Return EOD pre-move research candidates; never a trade execution endpoint."""
    if top_n < 1 or top_n > 100:
        raise ValueError("top_n must be between 1 and 100")

    snapshot = build_live_premove_snapshot(top_n=top_n)

    columns = [
        "SYMBOL", "ISIN", "TRADE_DATE", "CLSPRIC",
        "Setup_Score", "Chase_Risk", "Detector_Status",
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
    clean = clean.astype(object).where(pd.notna(clean), None)

    return {
        "system": "Money Machine",
        "module": "PreMovePatternDetector",
        "status": "RESEARCH_CANDIDATE_ONLY",
        "data_source": "Yahoo Finance EOD via yfinance; research fallback, not official NSE intraday data",
        "data_note": "Intraday VWAP and news/catalyst evidence are not fabricated; no automatic execution.",
        "candidates": clean.to_dict(orient="records"),
    }
