
from pathlib import Path

import pandas as pd


SPECIAL_SESSIONS = {
    pd.Timestamp("2026-02-01"),
}


def audit_index_calendar(
    prices: pd.DataFrame,
    holidays_path: str | Path = "data/market/calendar_audit.csv",
    year: int = 2026,
) -> dict:
    """Audit observed index dates against the configured annual calendar."""

    required = {"Date", "Open", "High", "Low", "Close"}
    missing_columns = sorted(required - set(prices.columns))

    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    df = prices.copy()
    df["Date"] = pd.to_datetime(
        df["Date"], errors="coerce"
    ).dt.normalize()

    if df["Date"].isna().any():
        raise ValueError("Invalid or missing dates found.")

    if df["Date"].duplicated().any():
        raise ValueError("Duplicate dates found.")

    start = pd.Timestamp(f"{year}-01-01")
    end = df.loc[
        df["Date"].dt.year.eq(year), "Date"
    ].max()

    if pd.isna(end):
        raise ValueError(f"No price data found for {year}.")

    calendar = pd.read_csv(holidays_path)

    required_calendar = {"TRADE_DATE", "STATUS"}
    if not required_calendar.issubset(calendar.columns):
        raise ValueError(
            f"Calendar must contain {sorted(required_calendar)}"
        )

    calendar["TRADE_DATE"] = pd.to_datetime(
        calendar["TRADE_DATE"], errors="raise"
    ).dt.normalize()

    calendar = calendar[
        calendar["TRADE_DATE"].dt.year.eq(year)
    ]

    holidays = set(
        calendar.loc[
            calendar["STATUS"].eq("HOLIDAY"), "TRADE_DATE"
        ]
    )

    weekdays = set(pd.date_range(start, end, freq="B"))
    special = {
        day for day in SPECIAL_SESSIONS
        if start <= day <= end
    }

    expected = (weekdays - holidays) | special

    actual = set(
        df.loc[
            df["Date"].between(start, end), "Date"
        ]
    )

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    actual_holidays = sorted(actual & holidays)

    return {
        "year": year,
        "start_date": start.date().isoformat(),
        "end_date": end.date().isoformat(),
        "actual_dates": len(actual),
        "expected_dates_from_config": len(expected),
        "missing_dates": [d.date().isoformat() for d in missing],
        "unexpected_dates": [
            d.date().isoformat() for d in unexpected
        ],
        "dates_on_listed_holidays": [
            d.date().isoformat() for d in actual_holidays
        ],
        "special_sessions": [
            d.date().isoformat() for d in sorted(special)
        ],
        "calendar_is_authoritative": False,
    }


if __name__ == "__main__":
    prices = pd.read_csv("data/raw/nifty50_daily_unified.csv")
    result = audit_index_calendar(prices)

    for key, value in result.items():
        print(f"{key}: {value}")
