from pathlib import Path

import pandas as pd

from .panel import build_research_panel
from .regime import build_regime_context


def reconcile_market_dates(
    start_date="2026-01-01",
    end_date="2026-10-01",
):
    # Stock-panel dates
    panel = build_research_panel(
        start_date,
        end_date,
    )

    stock_dates = pd.DatetimeIndex(
        sorted(panel["TRADE_DATE"].unique())
    )

    # NIFTY dates
    regime = build_regime_context()

    nifty_dates = pd.DatetimeIndex(
        sorted(
            regime.loc[
                (regime["TRADE_DATE"] >= start_date)
                & (regime["TRADE_DATE"] <= end_date),
                "TRADE_DATE",
            ].unique()
        )
    )

    stock_only = stock_dates.difference(nifty_dates)
    nifty_only = nifty_dates.difference(stock_dates)

    print("=== DATE RECONCILIATION ===")
    print(f"Stock-panel dates : {len(stock_dates)}")
    print(f"NIFTY dates       : {len(nifty_dates)}")
    print()

    print("Dates in stock panel but NOT NIFTY:")
    for date in stock_only:
        print(" ", date.date())

    print()

    print("Dates in NIFTY but NOT stock panel:")
    for date in nifty_only:
        print(" ", date.date())

    print()

    print("Common dates:", len(stock_dates.intersection(nifty_dates)))


if __name__ == "__main__":
    reconcile_market_dates()