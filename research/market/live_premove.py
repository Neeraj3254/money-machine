
"""Live EOD pre-move scanner using Yahoo Finance via yfinance.

Research fallback only. This is not official NSE BhavCopy or intraday data.
The scanner validates downloaded OHLCV data, avoids parallel batch downloads
during diagnosis, and fails explicitly when required benchmark data is absent.

No automatic trade execution. Successful data retrieval does not establish
that any signal is profitable or validated.
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

from .premove import add_premove_features, add_premove_scores


# Static NIFTY-50-style research universe.
# This is not a claim of historical or current index membership.
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

PRICE_COLUMNS = ["OPNPRIC", "HGHPRIC", "LWPRIC", "CLSPRIC"]
NUMERIC_COLUMNS = PRICE_COLUMNS + ["TTLTRADGVOL"]


def _ticker(symbol: str) -> str:
    """Convert an Indian equity symbol to its Yahoo Finance ticker."""
    return symbol if symbol.startswith("^") else f"{symbol}.NS"


def _download_history(
    tickers: str | list[str],
    *,
    period: str,
) -> pd.DataFrame:
    """Download daily history and convert provider failures into clear errors."""
    try:
        data = yf.download(
            tickers,
            period=period,
            interval="1d",
            auto_adjust=False,
            group_by="ticker",
            threads=False,
            progress=False,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Yahoo Finance download failed for {tickers!r}: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    if data is None or data.empty:
        raise RuntimeError(
            f"Yahoo Finance returned no daily history for {tickers!r}"
        )

    return data


def _one_symbol(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize one ticker's download and reject invalid OHLCV rows."""
    if raw is None or raw.empty:
        return pd.DataFrame()

    df = raw.copy()

    # yfinance may return (field, ticker) or (ticker, field) columns.
    if isinstance(df.columns, pd.MultiIndex):
        levels = [
            list(df.columns.get_level_values(i))
            for i in range(df.columns.nlevels)
        ]

        if symbol in levels[0]:
            df = df[symbol]
        elif symbol in levels[-1]:
            df = df.xs(symbol, axis=1, level=-1)
        else:
            return pd.DataFrame()

    rename = {
        "Open": "OPNPRIC",
        "High": "HGHPRIC",
        "Low": "LWPRIC",
        "Close": "CLSPRIC",
        "Volume": "TTLTRADGVOL",
    }
    df = df.rename(columns=rename)

    if any(column not in df.columns for column in NUMERIC_COLUMNS):
        return pd.DataFrame()

    df = df.reset_index()
    date_col = "Date" if "Date" in df.columns else df.columns[0]

    df["TRADE_DATE"] = pd.to_datetime(
        df[date_col], errors="coerce", utc=True
    ).dt.tz_localize(None)

    # Convert bad values to NaN, and remove non-finite numeric values.
    for column in NUMERIC_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.replace([float("inf"), float("-inf")], float("nan"))

    df = df.dropna(subset=["TRADE_DATE", *NUMERIC_COLUMNS])

    # Basic OHLCV integrity checks.
    valid_rows = (
        (df["OPNPRIC"] > 0)
        & (df["HGHPRIC"] > 0)
        & (df["LWPRIC"] > 0)
        & (df["CLSPRIC"] > 0)
        & (df["TTLTRADGVOL"] >= 0)
        & (df["HGHPRIC"] >= df["LWPRIC"])
        & (df["HGHPRIC"] >= df["OPNPRIC"])
        & (df["HGHPRIC"] >= df["CLSPRIC"])
        & (df["LWPRIC"] <= df["OPNPRIC"])
        & (df["LWPRIC"] <= df["CLSPRIC"])
    )

    df = df.loc[valid_rows].copy()

    if df.empty:
        return pd.DataFrame()

    df = (
        df.sort_values("TRADE_DATE")
        .drop_duplicates(subset=["TRADE_DATE"], keep="last")
        .reset_index(drop=True)
    )

    df["SYMBOL"] = symbol

    # Compatibility key for the existing feature pipeline.
    # This is a ticker surrogate, NOT an official security ISIN.
    df["ISIN"] = symbol

    df["PRVSCLSGPRIC"] = df["CLSPRIC"].shift(1)
    df["TTLTRFVAL"] = df["CLSPRIC"] * df["TTLTRADGVOL"]
    df["DATA_AVAILABLE"] = True

    return df[
        [
            "TRADE_DATE",
            "ISIN",
            "SYMBOL",
            "OPNPRIC",
            "HGHPRIC",
            "LWPRIC",
            "CLSPRIC",
            "PRVSCLSGPRIC",
            "TTLTRADGVOL",
            "TTLTRFVAL",
            "DATA_AVAILABLE",
        ]
    ]


def _download_nifty_context(period: str) -> pd.DataFrame:
    """Download and validate the NIFTY benchmark used for relative strength."""
    raw = _download_history("^NSEI", period=period)

    # Normalize possible MultiIndex columns.
    if isinstance(raw.columns, pd.MultiIndex):
        levels = [
            list(raw.columns.get_level_values(i))
            for i in range(raw.columns.nlevels)
        ]

        if "^NSEI" in levels[0]:
            raw = raw["^NSEI"]
        elif "^NSEI" in levels[-1]:
            raw = raw.xs("^NSEI", axis=1, level=-1)
        else:
            raw.columns = raw.columns.get_level_values(0)

    if "Close" not in raw.columns:
        raise RuntimeError(
            "NIFTY benchmark download has no Close column; "
            "relative-strength features cannot be trusted."
        )

    nifty = raw.reset_index()
    date_col = "Date" if "Date" in nifty.columns else nifty.columns[0]

    nifty["TRADE_DATE"] = pd.to_datetime(
        nifty[date_col], errors="coerce", utc=True
    ).dt.tz_localize(None)

    nifty["NIFTY_CLOSE"] = pd.to_numeric(
        nifty["Close"], errors="coerce"
    )

    nifty = nifty.replace(
        [float("inf"), float("-inf")], float("nan")
    )

    nifty = nifty.dropna(subset=["TRADE_DATE", "NIFTY_CLOSE"])
    nifty = nifty[nifty["NIFTY_CLOSE"] > 0]

    nifty = (
        nifty[["TRADE_DATE", "NIFTY_CLOSE"]]
        .sort_values("TRADE_DATE")
        .drop_duplicates(subset=["TRADE_DATE"], keep="last")
        .reset_index(drop=True)
    )

    if nifty.empty:
        raise RuntimeError(
            "NIFTY benchmark data is unavailable or invalid; "
            "cannot calculate relative-strength features reliably."
        )

    return nifty


def build_live_premove_snapshot(
    top_n: int = 25,
    period: str = "1y",
) -> pd.DataFrame:
    """Build an EOD research ranking; this function does not execute trades."""
    if not isinstance(top_n, int) or isinstance(top_n, bool):
        raise ValueError("top_n must be an integer")

    if top_n < 1 or top_n > 100:
        raise ValueError("top_n must be between 1 and 100")

    if not isinstance(period, str) or not period.strip():
        raise ValueError("period must be a non-empty string")

    symbols = list(dict.fromkeys(NIFTY50))
    yf_symbols = [_ticker(symbol) for symbol in symbols]

    raw = _download_history(yf_symbols, period=period)

    frames: list[pd.DataFrame] = []
    failed_symbols: list[str] = []

    for symbol in symbols:
        ticker = _ticker(symbol)

        try:
            df = _one_symbol(raw, ticker)
        except (KeyError, TypeError, ValueError) as exc:
            failed_symbols.append(f"{ticker}: {type(exc).__name__}")
            continue

        if df.empty:
            failed_symbols.append(ticker)
            continue

        frames.append(df)

    if not frames:
        raise RuntimeError(
            "No valid stock history was available for the research universe. "
            "Check Yahoo Finance access and the deployment logs."
        )

    panel = pd.concat(frames, ignore_index=True)

    # Benchmark is required. Do not silently calculate relative strength
    # without it.
    nifty = _download_nifty_context(period=period)

    features = add_premove_features(panel, nifty_context=nifty)

    if features is None or features.empty:
        raise RuntimeError(
            "Feature generation returned no rows from the available market data."
        )

    features = features.replace(
        [float("inf"), float("-inf")], float("nan")
    )

    latest = (
        features.sort_values(["ISIN", "TRADE_DATE"])
        .groupby("ISIN", as_index=False)
        .tail(1)
        .copy()
    )

    if latest.empty:
        raise RuntimeError(
            "No latest observations remain after feature generation."
        )

    scored = add_premove_scores(latest)

    if scored is None or scored.empty:
        raise RuntimeError("The scoring function returned no candidates.")

    # Sort and score using the existing scoring implementation.
    # Drop rows without the minimum required price and score fields.
    required_for_ranking = ["SYMBOL", "CLSPRIC", "Setup_Score"]
    missing_columns = [
        column
        for column in required_for_ranking
        if column not in scored.columns
    ]
    if missing_columns:
        raise RuntimeError(
            f"Scoring output is missing required fields: {missing_columns}"
        )

    scored["CLSPRIC"] = pd.to_numeric(
        scored["CLSPRIC"], errors="coerce"
    )
    scored["Setup_Score"] = pd.to_numeric(
        scored["Setup_Score"], errors="coerce"
    )

    scored = scored.replace(
        [float("inf"), float("-inf")], float("nan")
    )

    scored = scored.dropna(
        subset=["SYMBOL", "CLSPRIC", "Setup_Score"]
    )

    if scored.empty:
        raise RuntimeError(
            "No candidates have valid prices and ranking scores."
        )

# Rank by chase-adjusted score, with deterministic tie-breaking.
scored = scored.sort_values(
    ["Adjusted_Setup_Score", "Setup_Score", "SYMBOL"],
    ascending=[False, False, True],
    kind="stable",
)

    result = scored.head(top_n).reset_index(drop=True)

    # Attach download diagnostics for callers that choose to inspect them.
    # This is DataFrame metadata, not a candidate ranking feature.
    result.attrs["requested_symbols"] = len(symbols)
    result.attrs["symbols_with_data"] = len(frames)
    result.attrs["symbols_without_valid_data"] = failed_symbols
    result.attrs["benchmark"] = "^NSEI"
    result.attrs["data_source"] = "Yahoo Finance EOD via yfinance"

    return result
