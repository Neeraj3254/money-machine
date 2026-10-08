"""
Money Machine — Pre-Move Research Detector

Purpose:
    Build observable EOD features that identify stocks showing
    early signs of expansion, momentum, breakout structure,
    relative strength and liquidity.

Important:
    This module produces research features and ranking scores.
    It does NOT estimate probability of profit and does NOT
    authorize trade execution.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
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
]


def _require_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )


def _safe_divide(a, b):
    return np.where(
        pd.to_numeric(b, errors="coerce").replace(0, np.nan)
        if isinstance(b, pd.Series)
        else b,
        a / b,
        np.nan,
    )


def add_premove_features(
    df: pd.DataFrame,
    nifty_context: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Add pre-move research features.

    All features are constructed using information available
    on or before the current observation.

    No future-return target is created here.
    """

    _require_columns(df)

    result = df.copy()

    result["TRADE_DATE"] = pd.to_datetime(
        result["TRADE_DATE"],
        errors="coerce",
    )

    result = result.sort_values(
        ["ISIN", "TRADE_DATE"]
    ).reset_index(drop=True)

    numeric_columns = [
        "OPNPRIC",
        "HGHPRIC",
        "LWPRIC",
        "CLSPRIC",
        "PRVSCLSGPRIC",
        "TTLTRADGVOL",
        "TTLTRFVAL",
    ]

    for column in numeric_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    grouped = result.groupby("ISIN", group_keys=False)

    # ---------------------------------------------------------
    # Basic returns
    # ---------------------------------------------------------

    result["Return_1D"] = grouped["CLSPRIC"].pct_change(1)
    result["Return_3D"] = grouped["CLSPRIC"].pct_change(3)
    result["Return_5D"] = grouped["CLSPRIC"].pct_change(5)
    result["Return_10D"] = grouped["CLSPRIC"].pct_change(10)
    result["Return_20D"] = grouped["CLSPRIC"].pct_change(20)
    result["Return_50D"] = grouped["CLSPRIC"].pct_change(50)

    # ---------------------------------------------------------
    # Volume / RVOL
    # ---------------------------------------------------------

    for window in [5, 10, 20, 50]:
        average_volume = grouped["TTLTRADGVOL"].transform(
            lambda x, w=window: x.shift(1).rolling(w).mean()
        )

        result[f"RVOL_{window}D"] = (
            result["TTLTRADGVOL"] /
            average_volume.replace(0, np.nan)
        )

    # ---------------------------------------------------------
    # Price range / ATR-style expansion
    # ---------------------------------------------------------

    result["True_Range"] = (
        result["HGHPRIC"] - result["LWPRIC"]
    )

    previous_close = grouped["CLSPRIC"].shift(1)

    result["True_Range"] = pd.concat(
        [
            result["HGHPRIC"] - result["LWPRIC"],
            (result["HGHPRIC"] - previous_close).abs(),
            (result["LWPRIC"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    result["ATR_14"] = (
        result.groupby("ISIN")["True_Range"]
        .transform(
            lambda x: x.shift(1).rolling(14).mean()
        )
    )

    result["ATR_Range_Ratio"] = (
        result["True_Range"] /
        result["ATR_14"].replace(0, np.nan)
    )

    result["Range_Expansion"] = (
        result["ATR_Range_Ratio"] >= 1.5
    )

    # ---------------------------------------------------------
    # EMA structure
    # ---------------------------------------------------------

    for window in [20, 50, 200]:
        result[f"EMA_{window}"] = (
            grouped["CLSPRIC"]
            .transform(
                lambda x, w=window:
                x.ewm(span=w, adjust=False).mean()
            )
        )

    result["EMA_Bullish_20_50"] = (
        result["EMA_20"] > result["EMA_50"]
    )

    result["EMA_Bullish_50_200"] = (
        result["EMA_50"] > result["EMA_200"]
    )

    result["Above_EMA_20"] = (
        result["CLSPRIC"] > result["EMA_20"]
    )

    result["Above_EMA_50"] = (
        result["CLSPRIC"] > result["EMA_50"]
    )

    result["Above_EMA_200"] = (
        result["CLSPRIC"] > result["EMA_200"]
    )

    # ---------------------------------------------------------
    # Breakout structure
    # ---------------------------------------------------------

    for window in [5, 10, 20, 50]:
        prior_high = (
            grouped["HGHPRIC"]
            .transform(
                lambda x, w=window:
                x.shift(1).rolling(w).max()
            )
        )

        result[f"Breakout_{window}D"] = (
            result["CLSPRIC"] > prior_high
        )

    prior_52w_high = (
        grouped["HGHPRIC"]
        .transform(
            lambda x:
            x.shift(1).rolling(252).max()
        )
    )

    result["Breakout_52W"] = (
        result["CLSPRIC"] > prior_52w_high
    )

    # ---------------------------------------------------------
    # RSI
    # ---------------------------------------------------------

    delta = grouped["CLSPRIC"].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = (
        gain.groupby(result["ISIN"])
        .transform(
            lambda x: x.shift(1).rolling(14).mean()
        )
    )

    avg_loss = (
        loss.groupby(result["ISIN"])
        .transform(
            lambda x: x.shift(1).rolling(14).mean()
        )
    )

    rs = avg_gain / avg_loss.replace(0, np.nan)

    result["RSI_14"] = (
        100 - (100 / (1 + rs))
    )

    # ---------------------------------------------------------
    # MACD
    # ---------------------------------------------------------

    ema_12 = grouped["CLSPRIC"].transform(
        lambda x:
        x.ewm(span=12, adjust=False).mean()
    )

    ema_26 = grouped["CLSPRIC"].transform(
        lambda x:
        x.ewm(span=26, adjust=False).mean()
    )

    result["MACD"] = ema_12 - ema_26

    result["MACD_Signal"] = (
        result.groupby("ISIN")["MACD"]
        .transform(
            lambda x:
            x.ewm(span=9, adjust=False).mean()
        )
    )

    result["MACD_Bullish"] = (
        result["MACD"] > result["MACD_Signal"]
    )

    # ---------------------------------------------------------
    # Gap
    # ---------------------------------------------------------

    result["Gap_Pct"] = (
        result["OPNPRIC"] /
        result["PRVSCLSGPRIC"].replace(0, np.nan)
        - 1
    )

    result["Gap_Up"] = (
        result["Gap_Pct"] >= 0.01
    )

    result["Gap_Down"] = (
        result["Gap_Pct"] <= -0.01
    )

    # ---------------------------------------------------------
    # Pullback / recovery structure
    # ---------------------------------------------------------

    high_20 = (
        grouped["HGHPRIC"]
        .transform(
            lambda x:
            x.shift(1).rolling(20).max()
        )
    )

    result["Distance_From_20D_High"] = (
        result["CLSPRIC"] /
        high_20.replace(0, np.nan)
        - 1
    )

    result["Pullback_From_20D_High"] = (
        result["Distance_From_20D_High"] < -0.03
    )

    result["Near_20D_High"] = (
        result["Distance_From_20D_High"] >= -0.02
    )

    # ---------------------------------------------------------
    # Liquidity
    # ---------------------------------------------------------

    result["Liquidity_Turnover"] = (
        result["TTLTRFVAL"]
    )

    result["Liquidity_20D"] = (
        grouped["TTLTRFVAL"]
        .transform(
            lambda x:
            x.shift(1).rolling(20).mean()
        )
    )

    result["Liquid_Stock"] = (
        result["Liquidity_20D"] >= 10_000_000
    )

    # ---------------------------------------------------------
    # NIFTY relative strength
    # ---------------------------------------------------------

    if nifty_context is not None and not nifty_context.empty:

        nifty = nifty_context.copy()

        nifty["TRADE_DATE"] = pd.to_datetime(
            nifty["TRADE_DATE"],
            errors="coerce",
        )

        nifty["NIFTY_CLOSE"] = pd.to_numeric(
            nifty["NIFTY_CLOSE"],
            errors="coerce",
        )

        nifty = (
            nifty[
                ["TRADE_DATE", "NIFTY_CLOSE"]
            ]
            .drop_duplicates("TRADE_DATE")
            .sort_values("TRADE_DATE")
        )

        nifty["NIFTY_RETURN_1D"] = (
            nifty["NIFTY_CLOSE"].pct_change()
        )

        nifty["NIFTY_RETURN_5D"] = (
            nifty["NIFTY_CLOSE"].pct_change(5)
        )

        nifty["NIFTY_RETURN_20D"] = (
            nifty["NIFTY_CLOSE"].pct_change(20)
        )

        result = result.merge(
            nifty[
                [
                    "TRADE_DATE",
                    "NIFTY_CLOSE",
                    "NIFTY_RETURN_1D",
                    "NIFTY_RETURN_5D",
                    "NIFTY_RETURN_20D",
                ]
            ],
            on="TRADE_DATE",
            how="left",
        )

        result["Relative_Strength_NIFTY_1D"] = (
            result["Return_1D"]
            - result["NIFTY_RETURN_1D"]
        )

        result["Relative_Strength_NIFTY_5D"] = (
            result["Return_5D"]
            - result["NIFTY_RETURN_5D"]
        )

        result["Relative_Strength_NIFTY_20D"] = (
            result["Return_20D"]
            - result["NIFTY_RETURN_20D"]
        )

        result["NIFTY_Stronger"] = (
            result["Relative_Strength_NIFTY_20D"] > 0
        )

    else:

        result["NIFTY_CLOSE"] = np.nan
        result["NIFTY_RETURN_1D"] = np.nan
        result["NIFTY_RETURN_5D"] = np.nan
        result["NIFTY_RETURN_20D"] = np.nan

        result["Relative_Strength_NIFTY_1D"] = np.nan
        result["Relative_Strength_NIFTY_5D"] = np.nan
        result["Relative_Strength_NIFTY_20D"] = np.nan

        result["NIFTY_Stronger"] = False

    # ---------------------------------------------------------
    # Volume acceleration
    # ---------------------------------------------------------

    result["Volume_Acceleration_10D"] = (
        result["RVOL_5D"] /
        result["RVOL_20D"].replace(0, np.nan)
    )

    result["Volume_Shock"] = (
        result["RVOL_20D"] >= 2.0
    )

    # ---------------------------------------------------------
    # Basic bullish structure
    # ---------------------------------------------------------

    result["Trend_Bullish"] = (
        result["Above_EMA_20"]
        & result["EMA_Bullish_20_50"]
        & result["EMA_Bullish_50_200"]
    )

    result["Momentum_Bullish"] = (
        (result["Return_5D"] > 0)
        & (result["Return_20D"] > 0)
    )

    result["Breakout_Bullish"] = (
        result[
            [
                "Breakout_5D",
                "Breakout_10D",
                "Breakout_20D",
                "Breakout_50D",
                "Breakout_52W",
            ]
        ]
        .fillna(False)
        .any(axis=1)
    )

    return result


def add_premove_scores(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create a transparent research-ranking score.

    The score is NOT a probability and must never be interpreted
    as one.
    """

    result = df.copy()

    score = pd.Series(
        0.0,
        index=result.index,
    )

    # ---------------------------------------------------------
    # Volume expansion
    # ---------------------------------------------------------

    score += np.where(
        result["RVOL_5D"] >= 2.0,
        2.0,
        0.0,
    )

    score += np.where(
        result["RVOL_20D"] >= 1.5,
        1.0,
        0.0,
    )

    # ---------------------------------------------------------
    # Range expansion
    # ---------------------------------------------------------

    score += np.where(
        result["ATR_Range_Ratio"] >= 1.5,
        1.5,
        0.0,
    )

    # ---------------------------------------------------------
    # Trend
    # ---------------------------------------------------------

    score += np.where(
        result["Above_EMA_20"],
        0.5,
        0.0,
    )

    score += np.where(
        result["EMA_Bullish_20_50"],
        0.75,
        0.0,
    )

    score += np.where(
        result["EMA_Bullish_50_200"],
        0.75,
        0.0,
    )

    # ---------------------------------------------------------
    # Momentum
    # ---------------------------------------------------------

    score += np.where(
        result["Return_5D"] > 0,
        0.5,
        0.0,
    )

    score += np.where(
        result["Return_20D"] > 0,
        0.75,
        0.0,
    )

    # ---------------------------------------------------------
    # Breakout
    # ---------------------------------------------------------

    score += np.where(
        result["Breakout_5D"],
        0.75,
        0.0,
    )

    score += np.where(
        result["Breakout_20D"],
        1.0,
        0.0,
    )

    score += np.where(
        result["Breakout_50D"],
        1.0,
        0.0,
    )

    score += np.where(
        result["Breakout_52W"],
        1.25,
        0.0,
    )

    # ---------------------------------------------------------
    # RSI / MACD confirmation
    # ---------------------------------------------------------

    score += np.where(
        result["RSI_14"].between(50, 70),
        0.5,
        0.0,
    )

    score += np.where(
        result["MACD_Bullish"],
        0.5,
        0.0,
    )

    # ---------------------------------------------------------
    # Relative strength
    # ---------------------------------------------------------

    score += np.where(
        result["Relative_Strength_NIFTY_20D"] > 0,
        1.0,
        0.0,
    )

    # ---------------------------------------------------------
    # Liquidity
    # ---------------------------------------------------------

    score += np.where(
        result["Liquid_Stock"],
        0.5,
        0.0,
    )

    # ---------------------------------------------------------
    # Pullback quality
    # ---------------------------------------------------------

    score += np.where(
        result["Near_20D_High"],
        0.5,
        0.0,
    )

    # ---------------------------------------------------------
    # Anti-chase penalty
    # ---------------------------------------------------------

    chase_risk = pd.Series(
        0.0,
        index=result.index,
    )

    chase_risk += np.where(
        result["Return_1D"] >= 0.08,
        3.0,
        0.0,
    )

    chase_risk += np.where(
        result["Gap_Pct"] >= 0.05,
        2.0,
        0.0,
    )

    chase_risk += np.where(
        result["RVOL_5D"] >= 5.0,
        1.5,
        0.0,
    )

    chase_risk += np.where(
        result["ATR_Range_Ratio"] >= 3.0,
        1.5,
        0.0,
    )

    # Strong one-day move near highs can indicate late entry risk.
    chase_risk += np.where(
        (
            (result["Return_1D"] >= 0.05)
            & result["Near_20D_High"]
        ),
        1.5,
        0.0,
    )

    result["Setup_Score"] = score.round(3)

    result["Chase_Risk"] = chase_risk.round(3)

    result["Adjusted_Setup_Score"] = (
        result["Setup_Score"]
        - result["Chase_Risk"]
    ).round(3)

    # ---------------------------------------------------------
    # Research classification
    # ---------------------------------------------------------

    result["PreMove_Status"] = "WATCH"

    strong = (
        (result["Adjusted_Setup_Score"] >= 7.0)
        & (result["Chase_Risk"] < 4.0)
        & result["Liquid_Stock"]
    )

    candidate = (
        (result["Adjusted_Setup_Score"] >= 5.0)
        & (result["Chase_Risk"] < 5.0)
    )

    result.loc[candidate, "PreMove_Status"] = (
        "RESEARCH_CANDIDATE"
    )

    result.loc[strong, "PreMove_Status"] = (
        "HIGH_PRIORITY_RESEARCH"
    )

    # Explicitly flag dangerous chase conditions.
    result.loc[
        result["Chase_Risk"] >= 5.0,
        "PreMove_Status",
    ] = "CHASE_RISK"

    # Rank only for research prioritization.
    result["PreMove_Rank"] = (
        result["Adjusted_Setup_Score"]
        .rank(
            ascending=False,
            method="min",
        )
    )

    return result.sort_values(
        [
            "Adjusted_Setup_Score",
            "Setup_Score",
        ],
        ascending=False,
    ).reset_index(drop=True)
