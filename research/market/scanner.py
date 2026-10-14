from pathlib import Path

import pandas as pd

from .panel import (
    build_research_panel,
    filter_available_market_data,
)
from .features import add_price_features
from .market_context import attach_market_context


def build_market_snapshot(
    start_date="2026-01-01",
    end_date="2026-10-01",
) -> pd.DataFrame:
    """
    Build the latest available research snapshot
    for the current NSE equity universe.
    """

    # 1. Load broad market panel
    panel = build_research_panel(
        start_date,
        end_date,
    )

    # 2. Keep actual market observations only
    panel = filter_available_market_data(panel)

    # 3. Build stock-level features
    features = add_price_features(panel)

    # 4. Attach NIFTY market context
    features = attach_market_context(features)

    # 5. Keep latest available observation per ISIN
    features = features.sort_values(
        ["ISIN", "TRADE_DATE"]
    )

    latest = (
        features
        .groupby("ISIN", as_index=False)
        .tail(1)
        .copy()
    )

    return latest.reset_index(drop=True)


def validate_market_snapshot(
    snapshot: pd.DataFrame,
) -> dict:
    """
    Validate the latest market snapshot.
    """

    required = [
        "ISIN",
        "SYMBOL",
        "TRADE_DATE",
        "CLSPRIC",
        "Return_20D",
        "Return_60D",
        "Volatility_20D",
        "Volume_Ratio",
        "Drawdown_60D",
        "Regime",
    ]

    missing = [
        column
        for column in required
        if column not in snapshot.columns
    ]

    if missing:
        raise ValueError(
            f"Missing snapshot columns: {missing}"
        )

    return {
        "rows": len(snapshot),
        "unique_isins": snapshot["ISIN"].nunique(),
        "unique_symbols": snapshot["SYMBOL"].nunique(),
        "latest_date": snapshot["TRADE_DATE"].max(),
        "missing_close": int(
            snapshot["CLSPRIC"].isna().sum()
        ),
        "missing_regime": int(
            snapshot["Regime"].isna().sum()
        ),
    }


def apply_basic_quality_filter(
    snapshot: pd.DataFrame,
) -> pd.DataFrame:
    """
    Remove observations that are unsuitable for
    the initial candidate scan.

    This is a data-quality/liquidity screen,
    NOT an alpha strategy.
    """

    result = snapshot.copy()

    result = result[
        result["CLSPRIC"].notna()
    ]

    result = result[
        result["Return_20D"].notna()
    ]

    result = result[
        result["Return_60D"].notna()
    ]

    result = result[
        result["Volatility_20D"].notna()
    ]

    result = result[
        result["Volume_Ratio"].notna()
    ]

    result = result[
        result["CLSPRIC"] > 0
    ]

    return result.reset_index(drop=True)

def rank_candidates(
    snapshot: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rank stocks for further research.

    IMPORTANT:
    This is a research-prioritization score.
    It is NOT a probability of profit and NOT a validated alpha score.
    """

    result = apply_basic_quality_filter(
        snapshot
    ).copy()

    # Cross-sectional percentile ranks.
    result["Momentum_20D_Rank"] = (
        result["Return_20D"]
        .rank(pct=True)
    )

    result["Momentum_60D_Rank"] = (
        result["Return_60D"]
        .rank(pct=True)
    )

    result["Volume_Rank"] = (
        result["Volume_Ratio"]
        .rank(pct=True)
    )

    result["Volatility_Rank"] = (
        result["Volatility_20D"]
        .rank(pct=True)
    )

    # Higher price-vs-SMA means stronger trend.
    if "Price_vs_SMA20" in result.columns:
        result["Trend_20D_Rank"] = (
            result["Price_vs_SMA20"]
            .rank(pct=True)
        )
    else:
        result["Trend_20D_Rank"] = 0.5

    if "Price_vs_SMA50" in result.columns:
        result["Trend_50D_Rank"] = (
            result["Price_vs_SMA50"]
            .rank(pct=True)
        )
    else:
        result["Trend_50D_Rank"] = 0.5

    # Research-prioritization score.
    result["Research_Score"] = (
        0.25 * result["Momentum_20D_Rank"]
        + 0.20 * result["Momentum_60D_Rank"]
        + 0.15 * result["Trend_20D_Rank"]
        + 0.15 * result["Trend_50D_Rank"]
        + 0.10 * result["Volume_Rank"]
        + 0.15 * (1 - result["Volatility_Rank"])
    )

    result = result.sort_values(
        "Research_Score",
        ascending=False,
    )

    return result.reset_index(drop=True)