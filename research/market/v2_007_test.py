import pandas as pd

from research.market.panel import (
    build_research_panel,
    filter_available_market_data,
)

from research.market.features import add_price_features
from research.market.market_context import attach_market_context

from research.market.cross_sectional import (
    build_cross_sectional_dataset,
    assign_momentum_quantiles,
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


valid = research[
    (research["Regime"] == "BEAR_HIGH_VOL")
    & research["Forward_Return_20D"].notna()
    & research["Momentum_Quantile"].notna()
].copy()


dates = sorted(valid["TRADE_DATE"].unique())

n = len(dates)

periods = [
    ("PERIOD_1", dates[: n // 3]),
    ("PERIOD_2", dates[n // 3 : 2 * n // 3]),
    ("PERIOD_3", dates[2 * n // 3 :]),
]


print("=== V2-007 TEMPORAL STABILITY ===")


for name, period_dates in periods:

    period = valid[
        valid["TRADE_DATE"].isin(period_dates)
    ]

    q1 = period.loc[
        period["Momentum_Quantile"] == 1,
        "Forward_Return_20D",
    ]

    q5 = period.loc[
        period["Momentum_Quantile"] == 5,
        "Forward_Return_20D",
    ]

    q1_mean = q1.mean()
    q5_mean = q5.mean()

    print()
    print(name)
    print("Start:", min(period_dates))
    print("End:", max(period_dates))
    print("Observations:", len(period))
    print("Q1:", q1_mean)
    print("Q5:", q5_mean)
    print("Q1-Q5:", q1_mean - q5_mean)
    print("Q1 positive rate:", (q1 > 0).mean())
    print("Q5 positive rate:", (q5 > 0).mean())