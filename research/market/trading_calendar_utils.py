from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd
import requests


NSE_HOLIDAY_URL = "https://www.nseindia.com/api/holiday-master?type=trading"

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com/",
}


@dataclass
class CalendarAudit:
    trade_date: date
    weekday: str
    status: str
    reason: str


def fetch_nse_holidays() -> pd.DataFrame:
    """
    Fetch the official NSE trading holiday calendar.
    """

    response = requests.get(
        NSE_HOLIDAY_URL,
        headers=NSE_HEADERS,
        timeout=20,
    )

    response.raise_for_status()

    payload = response.json()

    records = []

    for category, holidays in payload.items():

        if not isinstance(holidays, list):
            continue

        for holiday in holidays:

            if "tradingDate" not in holiday:
                continue

            records.append(
                {
                    "DATE": pd.to_datetime(
                        holiday["tradingDate"],
                        format="%d-%b-%Y",
                    ).date(),

                    "WEEKDAY": holiday.get("weekDay"),

                    "DESCRIPTION": holiday.get(
                        "description"
                    ),

                    "CATEGORY": category,
                }
            )

    holidays_df = pd.DataFrame(records)

    if holidays_df.empty:
        raise ValueError("NSE holiday calendar returned no records")

    holidays_df = holidays_df.drop_duplicates(
        subset=["DATE"]
    ).sort_values("DATE")

    return holidays_df.reset_index(drop=True)


def classify_date(
    trade_date: date,
    holidays_df: pd.DataFrame,
) -> CalendarAudit:

    weekday = trade_date.strftime("%A")

    # Weekend
    if trade_date.weekday() >= 5:

        return CalendarAudit(
            trade_date=trade_date,
            weekday=weekday,
            status="WEEKEND",
            reason="Saturday/Sunday",
        )

    # NSE holiday
    holiday_match = holidays_df[
        holidays_df["DATE"] == trade_date
    ]

    if not holiday_match.empty:

        description = holiday_match.iloc[0]["DESCRIPTION"]

        return CalendarAudit(
            trade_date=trade_date,
            weekday=weekday,
            status="HOLIDAY",
            reason=str(description),
        )

    # Weekday not listed as holiday
    return CalendarAudit(
        trade_date=trade_date,
        weekday=weekday,
        status="TRADING_DAY_EXPECTED",
        reason="Weekday and not listed in NSE trading holidays",
    )


def audit_dates(dates) -> pd.DataFrame:
    """
    Audit a collection of dates against the official NSE holiday calendar.
    """

    holidays_df = fetch_nse_holidays()

    records = []

    for trade_date in dates:

        if isinstance(trade_date, str):
            trade_date = pd.to_datetime(trade_date).date()

        result = classify_date(
            trade_date,
            holidays_df,
        )

        records.append(
            {
                "TRADE_DATE": result.trade_date,
                "WEEKDAY": result.weekday,
                "STATUS": result.status,
                "REASON": result.reason,
            }
        )

    return pd.DataFrame(records)


def save_calendar_audit(
    df: pd.DataFrame,
    path="data/market/calendar_audit.csv",
):

    output_path = Path(path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_path,
        index=False,
    )

    return output_path

def audit_date_range(
    start_date,
    end_date,
    market_data_dir="data/market/normalized",
):
    """
    Audit every calendar date in a date range.

    Combines:
    - weekday/weekend classification
    - official NSE holiday calendar
    - local normalized market-data cache
    """

    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()

    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")

    holidays_df = fetch_nse_holidays()

    dates = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D",
    )

    records = []

    for timestamp in dates:

        trade_date = timestamp.date()

        calendar_result = classify_date(
            trade_date,
            holidays_df,
        )

        date_string = trade_date.isoformat()

        expected_file = (
            Path(market_data_dir)
            / f"market_{date_string}.parquet"
        )

        file_exists = expected_file.exists()

        if calendar_result.status == "HOLIDAY":
            data_status = "EXPECTED_MISSING"

        elif calendar_result.status == "WEEKEND":
            data_status = "EXPECTED_MISSING"

        elif file_exists:
            data_status = "AVAILABLE"

        else:
            data_status = "MISSING"

        records.append(
            {
                "TRADE_DATE": trade_date,
                "WEEKDAY": calendar_result.weekday,
                "MARKET_STATUS": calendar_result.status,
                "MARKET_REASON": calendar_result.reason,
                "DATA_STATUS": data_status,
                "DATA_FILE_EXISTS": file_exists,
            }
        )

    return pd.DataFrame(records)