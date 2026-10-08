"""Live EOD pre-move scanner using Yahoo Finance via yfinance.

This is a research fallback for environments where the normalized NSE BhavCopy
panel is not mounted. It is explicitly labeled as Yahoo-sourced EOD data and
never fabricates intraday VWAP/news evidence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import pandas as pd
import yfinance as yf

from .premove import add_premove_features, add_premove_scores

# Static NIFTY-50-style research universe. This is a research universe, not a
# claim that every symbol is a current constituent on every date.
NIFTY50 = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
    "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL",
    "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "ETERNAL",
    "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO",
    "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY",
    "ITC", "JIOFIN", "JSWSTEEL", "KOTAKBANK", "LT", "M&M",
    "MARUTI", "MAXHEALTH", "NESTLEIND", "NTPC", "ONGC", "POWERGRID",
    "RELIANCE", "SBILIFE", "SBIN", "SHRIRAMFIN", "SUNPHARMA", "TATACONSUM",
    "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN", "TRENT", "ULTRACEMCO",
]


def _ticker(symbol: str) -> str:
    return symbol if symbol.startswith("^") else f"{symbol}.NS"


def _one_symbol(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize one yfinance download result into Money Machine columns."""
    if raw is None or raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        # yfinance may return (field, ticker) or (ticker, field).
        levels = [list(raw.columns.get_level_values(i)) for i in range(raw.columns.nlevels)]
        if symbol in levels[0]:
            raw = raw[symbol]
        elif symbol in levels[-1]:
            raw = raw.xs(symbol, axis=1, level=-1)
        else:
            return pd.DataFrame()

    df = raw.copy()
    rename = {
        "Open": "OPNPRIC", "High": "HGHPRIC", "Low": "LWPRIC",
        "Close": "CLSPRIC", "Volume": "TTLTRADGVOL",
    }
    df = df.rename(columns=rename)
    required = ["OPNPRIC", "HGHPRIC", "LWPRIC", "CLSPRIC", "TTLTRADGVOL"]
    if any(c not in df.columns for c in required):
        return pd.DataFrame()
    df = df.reset_index()
    date_col = "Date" if "Date" in df.columns else df.columns[0]
    df["TRADE_DATE"] = pd.to_datetime(df[date_col], utc=True).dt.tz_localize(None)
    df["SYMBOL"] = symbol
    df["ISIN"] = symbol
    df["PRVSCLSGPRIC"] = df["CLSPRIC"].shift(1)
    df["TTLTRFVAL"] = df["CLSPRIC"] * df["TTLTRADGVOL"]
    df["DATA_AVAILABLE"] = True
    return df[[
        "TRADE_DATE", "ISIN", "SYMBOL", "OPNPRIC", "HGHPRIC", "LWPRIC",
        "CLSPRIC", "PRVSCLSGPRIC", "TTLTRADGVOL", "TTLTRFVAL", "DATA_AVAILABLE"
    ]]


def build_live_premove_snapshot(top_n: int = 25, period: str = "1y") -> pd.DataFrame:
    if top_n < 1 or top_n > 100:
        raise ValueError("top_n must be between 1 and 100")

    symbols = list(dict.fromkeys(NIFTY50))
    yf_symbols = [_ticker(s) for s in symbols]
    raw = yf.download(
        yf_symbols,
        period=period,
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        threads=True,
        progress=False,
    )

    frames = []
    for symbol in symbols:
        df = _one_symbol(raw, _ticker(symbol))
        if not df.empty:
            frames.append(df)
    if not frames:
        raise RuntimeError("No Yahoo Finance EOD data returned for the research universe")

    panel = pd.concat(frames, ignore_index=True)

    nifty_raw = yf.download(
        "^NSEI",
        period=period,
        interval="1d",
        auto_adjust=False,
        progress=False,
    )
    if isinstance(nifty_raw.columns, pd.MultiIndex):
        nifty_raw.columns = nifty_raw.columns.get_level_values(0)
    nifty = nifty_raw.reset_index()
    date_col = "Date" if "Date" in nifty.columns else nifty.columns[0]
    nifty["TRADE_DATE"] = pd.to_datetime(nifty[date_col], utc=True).dt.tz_localize(None)
    nifty["NIFTY_CLOSE"] = pd.to_numeric(nifty["Close"], errors="coerce")
    nifty = nifty[["TRADE_DATE", "NIFTY_CLOSE"]].dropna()

    features = add_premove_features(panel, nifty_context=nifty)
    latest = (
        features.sort_values(["ISIN", "TRADE_DATE"])
        .groupby("ISIN", as_index=False)
        .tail(1)
        .copy()
    )
    return add_premove_scores(latest).head(top_n).reset_index(drop=True)
