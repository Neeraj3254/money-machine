from __future__ import annotations
import io
import zipfile
from pathlib import Path
import requests
LEGACY_BASE_URL = (
    "https://archives.nseindia.com/content/historical/EQUITIES"
)
RAW_DATA_DIR = Path("data/market/raw")
HEADERS = {
    "User-Agent": "Mozilla/5.0",
}
def build_legacy_url(trade_date: str) -> str:
    date = trade_date.replace("-", "")
    year = trade_date[:4]
    month = trade_date[5:7]
    month_name = {
        "01": "JAN",
        "02": "FEB",
        "03": "MAR",
        "04": "APR",
        "05": "MAY",
        "06": "JUN",
        "07": "JUL",
        "08": "AUG",
        "09": "SEP",
        "10": "OCT",
        "11": "NOV",
        "12": "DEC",
    }[month]
    day = date[6:8]
    filename = f"cm{day}{month_name}{year}bhav.csv.zip"
    return f"{LEGACY_BASE_URL}/{year}/{month_name}/{filename}"
def download_legacy_bhavcopy(
    trade_date: str,
    timeout: int = 30,
) -> dict:
    """Download and extract one legacy NSE Bhavcopy."""
    url = build_legacy_url(trade_date)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filename = url.rsplit("/", 1)[-1]
    zip_path = RAW_DATA_DIR / filename
    csv_filename = filename.removesuffix(".zip")
    csv_path = RAW_DATA_DIR / csv_filename
    if csv_path.exists():
        return {
            "status": "CACHED",
            "trade_date": trade_date,
            "url": url,
            "path": str(csv_path),
        }
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=timeout,
    )
    if response.status_code == 404:
        return {
            "status": "UNAVAILABLE",
            "trade_date": trade_date,
            "url": url,
            "reason": "NSE archive returned HTTP 404",
        }
    response.raise_for_status()
    zip_path.write_bytes(response.content)
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(RAW_DATA_DIR)
    return {
        "status": "DOWNLOADED",
        "trade_date": trade_date,
        "url": url,
        "path": str(csv_path),
        "size_bytes": csv_path.stat().st_size,
    }
