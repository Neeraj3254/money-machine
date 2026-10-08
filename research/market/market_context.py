import pandas as pd

from .regime import build_regime_context


def attach_market_context(
    stock_panel: pd.DataFrame,
    regime_context: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Attach NIFTY market-regime context to each stock observation.

    Join key:
        TRADE_DATE

    The market context is calculated independently from NIFTY data.
    No future market information is introduced by this join.
    """

    required_stock_columns = [
        "TRADE_DATE",
        "ISIN",
        "SYMBOL",
    ]

    missing_stock = [
        column
        for column in required_stock_columns
        if column not in stock_panel.columns
    ]

    if missing_stock:
        raise ValueError(
            f"Missing stock-panel columns: {missing_stock}"
        )

    if regime_context is None:
        regime_context = build_regime_context()

    required_regime_columns = [
        "TRADE_DATE",
        "NIFTY_CLOSE",
        "NIFTY_RETURN_20D",
        "NIFTY_RETURN_60D",
        "NIFTY_SMA20",
        "NIFTY_SMA50",
        "NIFTY_SMA200",
        "NIFTY_PRICE_VS_SMA20",
        "NIFTY_PRICE_VS_SMA50",
        "NIFTY_PRICE_VS_SMA200",
        "NIFTY_VOLATILITY_20D",
        "NIFTY_DRAWDOWN_252D",
        "Trend_Regime",
        "Volatility_Regime",
        "Regime",
    ]

    missing_regime = [
        column
        for column in required_regime_columns
        if column not in regime_context.columns
    ]

    if missing_regime:
        raise ValueError(
            f"Missing regime-context columns: {missing_regime}"
        )

    stock = stock_panel.copy()
    regime = regime_context.copy()

    stock["TRADE_DATE"] = pd.to_datetime(
        stock["TRADE_DATE"]
    )

    regime["TRADE_DATE"] = pd.to_datetime(
        regime["TRADE_DATE"]
    )

    if regime["TRADE_DATE"].duplicated().any():
        raise ValueError(
            "Regime context contains duplicate TRADE_DATE values."
        )

    overlapping_columns = [
        column
        for column in required_regime_columns
        if column != "TRADE_DATE"
        and column in stock.columns
    ]

    if overlapping_columns:
        raise ValueError(
            "Stock panel already contains regime columns: "
            f"{overlapping_columns}"
        )

    result = stock.merge(
        regime[required_regime_columns],
        on="TRADE_DATE",
        how="left",
        validate="many_to_one",
    )

    return result


def validate_market_context(
    df: pd.DataFrame,
) -> dict:
    """
    Validate the stock + market-context dataset.
    """

    required_columns = [
        "TRADE_DATE",
        "ISIN",
        "SYMBOL",
        "NIFTY_CLOSE",
        "Regime",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing validation columns: {missing}"
        )

    result = {
        "rows": len(df),
        "unique_symbols": df["SYMBOL"].nunique(),
        "unique_isins": df["ISIN"].nunique(),
        "unique_dates": df["TRADE_DATE"].nunique(),
        "missing_nifty_close": int(
            df["NIFTY_CLOSE"].isna().sum()
        ),
        "missing_regime": int(
            df["Regime"].isna().sum()
        ),
        "duplicate_date_isin": int(
            df.duplicated(
                ["TRADE_DATE", "ISIN"]
            ).sum()
        ),
    }

    return result