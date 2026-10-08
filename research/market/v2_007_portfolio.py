from research.market.panel import (
    build_research_panel,
    filter_available_market_data,
)

from research.market.features import add_price_features
from research.market.market_context import attach_market_context

from research.market.cross_sectional import (
    build_cross_sectional_dataset,
    assign_momentum_quantiles,
    simulate_quantile_portfolio,
)


panel = build_research_panel(
    "2026-01-01",
    "2026-10-01",
)

panel = filter_available_market_data(panel)

features = add_price_features(panel)

features = attach_market_context(features)

research = build_cross_sectional_dataset(features)

research = assign_momentum_quantiles(research)


# Only evaluate the regime where V2-007 was discovered.
research = research[
    research["Regime"] == "BEAR_HIGH_VOL"
].copy()


q1 = simulate_quantile_portfolio(
    research,
    quantile=1,
)

q5 = simulate_quantile_portfolio(
    research,
    quantile=5,
)

market = simulate_quantile_portfolio(
    research,
    quantile=None,
)


def summarize(df, name):

    print()
    print("===", name, "===")

    print("Days:", len(df))

    print(
        "Mean gross:",
        df["GROSS_RETURN"].mean(),
    )

    print(
        "Mean turnover:",
        df["TURNOVER"].mean(),
    )

    print(
        "Mean transaction cost:",
        df["TRANSACTION_COST"].mean(),
    )

    print(
        "Mean net:",
        df["NET_RETURN"].mean(),
    )

    print(
        "Median net:",
        df["NET_RETURN"].median(),
    )

    print(
        "Positive days:",
        (df["NET_RETURN"] > 0).mean(),
    )

    print(
        "Best day:",
        df["NET_RETURN"].max(),
    )

    print(
        "Worst day:",
        df["NET_RETURN"].min(),
    )


print("=== V2-007 REGIME-CONDITIONAL PORTFOLIO ===")

summarize(q1, "Q1")

summarize(q5, "Q5")

summarize(market, "MARKET")

def performance_metrics(df, name):

    returns = df["NET_RETURN"].dropna()

    equity = (1 + returns).cumprod()

    running_peak = equity.cummax()

    drawdown = (
        equity / running_peak
    ) - 1

    total_return = equity.iloc[-1] - 1

    max_drawdown = drawdown.min()

    annualized_volatility = (
        returns.std() * (252 ** 0.5)
    )

    annualized_return = (
        (1 + total_return)
        ** (252 / len(returns))
    ) - 1

    if returns.std() != 0:
        sharpe = (
            returns.mean()
            / returns.std()
        ) * (252 ** 0.5)
    else:
        sharpe = float("nan")

    print()
    print("===", name, "PERFORMANCE ===")
    print("Trading days:", len(returns))
    print("Total compounded return:", total_return)
    print("Annualized return:", annualized_return)
    print("Annualized volatility:", annualized_volatility)
    print("Maximum drawdown:", max_drawdown)
    print("Sharpe:", sharpe)


# Run performance analysis AFTER the function definition.
performance_metrics(q1, "Q1")
performance_metrics(q5, "Q5")
performance_metrics(market, "MARKET")