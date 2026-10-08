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


LIQUIDITY_THRESHOLD = 10_000_000  # ₹1 crore


def performance_metrics(portfolio):
    daily = portfolio["NET_RETURN"]

    cumulative = (1 + daily).prod() - 1

    annualized_return = (
        (1 + cumulative) ** (252 / len(daily)) - 1
        if len(daily) > 0
        else float("nan")
    )

    annualized_volatility = daily.std() * (252 ** 0.5)

    sharpe = (
        daily.mean() / daily.std() * (252 ** 0.5)
        if daily.std() != 0
        else float("nan")
    )

    equity_curve = (1 + daily).cumprod()
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    max_drawdown = drawdown.min()

    return {
        "days": len(daily),
        "mean_net_return": daily.mean(),
        "median_net_return": daily.median(),
        "positive_days": (daily > 0).mean(),
        "best_day": daily.max(),
        "worst_day": daily.min(),
        "compounded_return": cumulative,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
    }


def print_metrics(name, metrics):
    print()
    print(name)
    print("-" * len(name))

    for key, value in metrics.items():
        print(f"{key}: {value}")


def main():

    print("Loading market data...")

    panel = build_research_panel(
        "2026-01-01",
        "2026-10-01",
    )

    panel = filter_available_market_data(panel)

    features = add_price_features(panel)

    features = attach_market_context(features)

    research = build_cross_sectional_dataset(features)

    research = assign_momentum_quantiles(research)

    # ---------------------------------------------------------
    # BEAR_HIGH_VOL universe
    # ---------------------------------------------------------

    research = research[
        research["Regime"] == "BEAR_HIGH_VOL"
    ].copy()

    print()
    print("BEAR_HIGH_VOL UNIVERSE")
    print("----------------------")
    print(f"Observations: {len(research):,}")
    print(f"Trading dates: {research['TRADE_DATE'].nunique():,}")
    print(f"Unique securities: {research['ISIN'].nunique():,}")

    # ---------------------------------------------------------
    # Liquidity filter
    # ---------------------------------------------------------

    research = research[
        research["TTLTRFVAL"] >= LIQUIDITY_THRESHOLD
    ].copy()

    print()
    print("AFTER LIQUIDITY FILTER")
    print("----------------------")
    print(f"Threshold: ₹{LIQUIDITY_THRESHOLD:,.0f}")
    print(f"Observations: {len(research):,}")
    print(f"Trading dates: {research['TRADE_DATE'].nunique():,}")
    print(f"Unique securities: {research['ISIN'].nunique():,}")

    # Q1-specific diagnostics
    q1_universe = research[
        research["Momentum_Quantile"] == 1
    ].copy()

    print()
    print("FILTERED Q1 UNIVERSE")
    print("--------------------")
    print(f"Observations: {len(q1_universe):,}")
    print(f"Trading dates: {q1_universe['TRADE_DATE'].nunique():,}")
    print(f"Unique securities: {q1_universe['ISIN'].nunique():,}")
    print(
        "Average Q1 stocks/day:",
        round(
            q1_universe.groupby("TRADE_DATE")["ISIN"]
            .nunique()
            .mean(),
            2,
        ),
    )

    # ---------------------------------------------------------
    # Q1 portfolio
    # ---------------------------------------------------------

    q1 = simulate_quantile_portfolio(
        research,
        quantile=1,
        cost_per_turnover=0.001,
    )

    # ---------------------------------------------------------
    # Q5 comparison
    # ---------------------------------------------------------

    q5 = simulate_quantile_portfolio(
        research,
        quantile=5,
        cost_per_turnover=0.001,
    )

    # ---------------------------------------------------------
    # Market comparison
    # ---------------------------------------------------------

    market = simulate_quantile_portfolio(
        research,
        quantile=None,
        cost_per_turnover=0.001,
    )

    # ---------------------------------------------------------
    # Performance
    # ---------------------------------------------------------

    q1_metrics = performance_metrics(q1)
    q5_metrics = performance_metrics(q5)
    market_metrics = performance_metrics(market)

    print_metrics("Q1 PERFORMANCE", q1_metrics)

    print_metrics("Q5 PERFORMANCE", q5_metrics)

    print_metrics("MARKET PERFORMANCE", market_metrics)


if __name__ == "__main__":
    main()