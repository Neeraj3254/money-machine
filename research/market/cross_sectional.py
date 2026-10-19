import pandas as pd

from .costs import (
    calculate_portfolio_turnover,
    calculate_transaction_cost,
    calculate_net_return,
)

from .trading_calendar import (
    build_trading_calendar,
    attach_trading_session,
)

def build_cross_sectional_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build a cross-sectional research dataset using the
    actual stock observation calendar.

    The target is 20 available stock research sessions
    into the future for the same security.
    """

    required = [
        "TRADE_DATE",
        "ISIN",
        "SYMBOL",
        "CLSPRIC",
        "Return_20D",
        "Regime",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    result = df.copy()

    result["TRADE_DATE"] = pd.to_datetime(
        result["TRADE_DATE"]
    )

    # --------------------------------------------------
    # IMPORTANT:
    # Use the actual stock observation dates.
    #
    # Do NOT use the NIFTY calendar here because
    # NIFTY can contain sessions where no stock
    # observations exist.
    # --------------------------------------------------

    stock_dates = (
        result["TRADE_DATE"]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .reset_index(drop=True)
    )

    calendar = pd.DataFrame(
        {
            "TRADE_DATE": stock_dates,
            "TRADING_SESSION": range(len(stock_dates)),
        }
    )

    result = result.merge(
        calendar,
        on="TRADE_DATE",
        how="left",
        validate="many_to_one",
    )

    result = result.sort_values(
        ["ISIN", "TRADE_DATE"]
    ).reset_index(drop=True)

    # 20 actual stock research sessions forward
    result["TARGET_SESSION"] = (
        result["TRADING_SESSION"] + 20
    )

    session_to_date = calendar.rename(
        columns={
            "TRADING_SESSION": "TARGET_SESSION",
            "TRADE_DATE": "TARGET_DATE",
        }
    )

    result = result.merge(
        session_to_date,
        on="TARGET_SESSION",
        how="left",
        validate="many_to_one",
    )

    # Same security's close on the target date
    future_prices = (
        result[
            ["ISIN", "TRADE_DATE", "CLSPRIC"]
        ]
        .rename(
            columns={
                "TRADE_DATE": "TARGET_DATE",
                "CLSPRIC": "TARGET_CLOSE",
            }
        )
    )

    result = result.merge(
        future_prices,
        on=["ISIN", "TARGET_DATE"],
        how="left",
    )

    result["Forward_Return_20D"] = (
        result["TARGET_CLOSE"]
        / result["CLSPRIC"]
        - 1
    )

    return result

def add_next_session_return(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add the next available stock-session close and return
    for each security.

    The shift is performed within each ISIN, so the next
    observation is the next available stock session for
    that security.
    """

    required = [
        "ISIN",
        "TRADE_DATE",
        "CLSPRIC",
    ]

    missing = [
        col for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
        )

    result = df.copy()

    result["TRADE_DATE"] = pd.to_datetime(
        result["TRADE_DATE"]
    )

    result = result.sort_values(
        ["ISIN", "TRADE_DATE"]
    ).reset_index(drop=True)

    result["NEXT_CLOSE"] = (
        result.groupby("ISIN")["CLSPRIC"]
        .shift(-1)
    )

    result["NEXT_RETURN_1D"] = (
        result["NEXT_CLOSE"]
        / result["CLSPRIC"]
        - 1
    )

    return result

def assign_momentum_quantiles(
    df: pd.DataFrame,
    quantiles: int = 5,
) -> pd.DataFrame:
    """
    Rank stocks cross-sectionally on each date
    using ONLY their historical 20D return.
    """

    result = df.copy()

    def assign_group(group):
        group = group.copy()

        valid = group["Return_20D"].notna()

        group["Momentum_Quantile"] = pd.NA

        if valid.sum() >= quantiles:
            ranked = pd.qcut(
                group.loc[valid, "Return_20D"],
                q=quantiles,
                labels=False,
                duplicates="drop",
            )

            group.loc[
                valid,
                "Momentum_Quantile",
            ] = ranked + 1

        return group

    groups = []

    for _, group in result.groupby(
        "TRADE_DATE",
        sort=False,
    ):
        groups.append(
            assign_group(group)
        )

    result = pd.concat(
        groups,
        ignore_index=True,
    )

    result["Momentum_Quantile"] = pd.to_numeric(
        result["Momentum_Quantile"],
        errors="coerce",
    )

    return result

def summarize_momentum_test(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare future returns across momentum groups.
    """

    valid = df[
        df["Momentum_Quantile"].notna()
        & df["Forward_Return_20D"].notna()
    ].copy()

    summary = (
        valid
        .groupby("Momentum_Quantile")
        .agg(
            observations=(
                "Forward_Return_20D",
                "size",
            ),
            average_forward_return=(
                "Forward_Return_20D",
                "mean",
            ),
            positive_rate=(
                "Forward_Return_20D",
                lambda x: (x > 0).mean(),
            ),
        )
        .reset_index()
    )

    return summary

def calculate_daily_momentum_spread(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate the daily cross-sectional Q5 minus Q1
    forward-return spread.

    Q5 = strongest past 20D momentum
    Q1 = weakest past 20D momentum
    """

    valid = df[
        df["Momentum_Quantile"].notna()
        & df["Forward_Return_20D"].notna()
    ].copy()

    daily = (
        valid
        .groupby(
            [
                "TRADE_DATE",
                "Trend_Regime",
                "Volatility_Regime",
            ]
        )
        .agg(
            Q1_return=(
                "Forward_Return_20D",
                lambda x: x[
                    valid.loc[x.index, "Momentum_Quantile"] == 1
                ].mean(),
            ),
            Q5_return=(
                "Forward_Return_20D",
                lambda x: x[
                    valid.loc[x.index, "Momentum_Quantile"] == 5
                ].mean(),
            ),
        )
        .reset_index()
    )

    daily["Q5_minus_Q1"] = (
        daily["Q5_return"]
        - daily["Q1_return"]
    )

    return daily

def summarize_momentum_spread(
    df: pd.DataFrame,
) -> dict:
    """
    Compare the strongest momentum group against
    the eligible cross-sectional baseline.

    This is descriptive research, not a trading signal.
    """

    valid = df[
        df["Momentum_Quantile"].notna()
        & df["Forward_Return_20D"].notna()
    ].copy()

    baseline = (
        valid["Forward_Return_20D"]
        .mean()
    )

    q5 = (
        valid.loc[
            valid["Momentum_Quantile"] == 5,
            "Forward_Return_20D",
        ]
        .mean()
    )

    q1 = (
        valid.loc[
            valid["Momentum_Quantile"] == 1,
            "Forward_Return_20D",
        ]
        .mean()
    )

    return {
        "baseline_return": baseline,
        "q1_return": q1,
        "q5_return": q5,
        "q5_vs_baseline": q5 - baseline,
        "q5_minus_q1": q5 - q1,
        "q5_positive_rate": (
            valid.loc[
                valid["Momentum_Quantile"] == 5,
                "Forward_Return_20D",
            ] > 0
        ).mean(),
    }

def simulate_quantile_portfolio(
    df,
    quantile,
    cost_per_turnover=0.001,
):
    """
    Simulate a daily-rebalanced momentum quantile portfolio.

    quantile:
        1 = weakest momentum
        5 = strongest momentum
        None = entire eligible universe
    """

    required_columns = [
        "TRADE_DATE",
        "ISIN",
        "Momentum_Quantile",
        "CLSPRIC",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    result = df.copy()

    result = result.sort_values(
        ["TRADE_DATE", "ISIN"]
    ).reset_index(drop=True)

    result["NEXT_CLOSE"] = (
        result.groupby("ISIN")["CLSPRIC"]
        .shift(-1)
    )

    result["NEXT_RETURN"] = (
        result["NEXT_CLOSE"] / result["CLSPRIC"]
    ) - 1

    daily_results = []
    previous_symbols = set()

    for trade_date, day in result.groupby("TRADE_DATE"):

        if quantile is None:
            portfolio = day[
                day["NEXT_RETURN"].notna()
            ].copy()
        else:
            portfolio = day[
                (day["Momentum_Quantile"] == quantile)
                & day["NEXT_RETURN"].notna()
            ].copy()

        if portfolio.empty:
            continue

        current_symbols = set(portfolio["ISIN"])

        gross_return = portfolio["NEXT_RETURN"].mean()

        turnover = calculate_portfolio_turnover(
            previous_symbols,
            current_symbols,
        )

        transaction_cost = calculate_transaction_cost(
            turnover,
            cost_per_turnover,
        )

        net_return = calculate_net_return(
            gross_return,
            transaction_cost,
        )

        daily_results.append(
            {
                "TRADE_DATE": trade_date,
                "STOCKS": len(current_symbols),
                "GROSS_RETURN": gross_return,
                "TURNOVER": turnover,
                "TRANSACTION_COST": transaction_cost,
                "NET_RETURN": net_return,
            }
        )

        previous_symbols = current_symbols

    return pd.DataFrame(daily_results)