from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="Money Machine API",
    version="0.2.0",
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
        "version": "0.2.0",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    return {
        "system": "Money Machine",
        "analysis_status": "research_only",
        "asset": request.asset,
        "capital": request.capital,
        "horizon_days": request.horizon_days,
        "max_loss_percent": request.max_loss_percent,
        "decision": "NO TRADE",
        "reason": "Research engine is connected, but no validated market model is active yet.",
    }