import pandas as pd


def build_trading_calendar(
    start_date="2026-01-01",
    end_date="2026-10-01",
) -> pd.DataFrame:
    """
    Build the actual market-observation calendar from NIFTY data.

    Each row represents a date on which NIFTY has an observation.
    """

    from .regime import build_regime_context

    regime = build_regime_context()

    calendar = regime[
        [
            "TRADE_DATE",
            "NIFTY_CLOSE",
        ]
    ].copy()

    calendar["TRADE_DATE"] = pd.to_datetime(
        calendar["TRADE_DATE"]
    )

    calendar = calendar[
        (calendar["TRADE_DATE"] >= start_date)
        & (calendar["TRADE_DATE"] <= end_date)
    ].copy()

    calendar = (
        calendar
        .sort_values("TRADE_DATE")
        .drop_duplicates("TRADE_DATE")
        .reset_index(drop=True)
    )

    calendar["TRADING_SESSION"] = (
        range(len(calendar))
    )

    return calendar


def attach_trading_session(
    df: pd.DataFrame,
    calendar: pd.DataFrame,
) -> pd.DataFrame:
    """
    Attach the exchange-session number to stock observations.
    """

    result = df.copy()

    result["TRADE_DATE"] = pd.to_datetime(
        result["TRADE_DATE"]
    )

    calendar_dates = calendar[
        [
            "TRADE_DATE",
            "TRADING_SESSION",
        ]
    ].copy()

    result = result.merge(
        calendar_dates,
        on="TRADE_DATE",
        how="left",
        validate="many_to_one",
    )

    if result["TRADING_SESSION"].isna().any():
        missing_dates = (
            result.loc[
                result["TRADING_SESSION"].isna(),
                "TRADE_DATE",
            ]
            .drop_duplicates()
            .sort_values()
        )

        raise ValueError(
            "Stock observations contain dates missing "
            f"from the trading calendar: {missing_dates.tolist()}"
        )

    return result