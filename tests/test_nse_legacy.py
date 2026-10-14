from pathlib import Path
from research.market.nse_legacy import (
    read_legacy_bhavcopy,
    normalize_legacy_bhavcopy,
)
FIXTURE = Path("data/market/raw/cm04JAN2021bhav.csv")
def test_read_legacy_bhavcopy():
    df = read_legacy_bhavcopy(FIXTURE)
    assert len(df) == 2074
    assert "Unnamed: 13" not in df.columns
    assert "SYMBOL" in df.columns
    assert "ISIN" in df.columns
def test_normalize_legacy_bhavcopy():
    df = read_legacy_bhavcopy(FIXTURE)
    normalized = normalize_legacy_bhavcopy(df)
    assert len(normalized) == 1494
    assert normalized["SERIES"].eq("EQ").all()
    assert normalized["ISIN"].duplicated().sum() == 0
    assert normalized["CLSPRIC"].notna().all()
    assert normalized["TRADE_DATE"].dt.strftime("%Y-%m-%d").eq(
        "2021-01-04"
    ).all()
    assert normalized["DATA_AVAILABLE"].all()
