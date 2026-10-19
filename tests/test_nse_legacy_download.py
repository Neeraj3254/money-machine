from pathlib import Path
from research.market.nse_legacy_download import (
    build_legacy_url,
)
def test_build_legacy_url_january_2021():
    url = build_legacy_url("2021-01-04")
    assert url.endswith(
        "/2021/JAN/cm04JAN2021bhav.csv.zip"
    )
def test_build_legacy_url_july_2024():
    url = build_legacy_url("2024-07-05")
    assert url.endswith(
        "/2024/JUL/cm05JUL2024bhav.csv.zip"
    )
def test_build_legacy_url_december():
    url = build_legacy_url("2023-12-29")
    assert url.endswith(
        "/2023/DEC/cm29DEC2023bhav.csv.zip"
    )
