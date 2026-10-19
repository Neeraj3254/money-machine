
from datetime import date, timedelta
from pathlib import Path
import hashlib
import io
import json
import zipfile

import requests

from research.market.nse_daily import build_bhavcopy_url


RAW_DATA_DIR = Path("data/market/raw")
MANIFEST_DIR = Path("data/manifests")
MANIFEST_PATH = MANIFEST_DIR / "manifest.json"



def expected_zip_path(day: str) -> Path:
    """Return the expected local ZIP path for an NSE trading date."""
    parsed_day = date.fromisoformat(day)
    filename = (
        f"BhavCopy_NSE_CM_0_0_0_{parsed_day:%Y%m%d}_F_0000.csv.zip"
    )
    return RAW_DATA_DIR / filename



def sha256_file(path: Path) -> str:
    """Calculate the SHA-256 checksum of a file."""
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def validate_nse_zip(content: bytes) -> None:
    """
    Validate ZIP integrity, require at least one CSV, and test
    the integrity of every archive member.

    Raises BadZipFile for invalid ZIP data and ValueError when
    the archive has no CSV file or contains a corrupt member.
    """
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()

        if not any(name.lower().endswith(".csv") for name in names):
            raise ValueError("NSE ZIP contains no CSV file.")

        bad_member = archive.testzip()

        if bad_member is not None:
            raise ValueError(
                f"NSE ZIP has a corrupt member: {bad_member}"
            )


def load_manifest() -> dict:
    """Load the manifest, creating an empty one if necessary."""
    if not MANIFEST_PATH.exists():
        return {}

    with MANIFEST_PATH.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    if not isinstance(manifest, dict):
        raise ValueError("Manifest must contain a JSON object.")

    return manifest


def save_manifest(manifest: dict) -> None:
    """Persist the manifest as formatted JSON."""
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    with MANIFEST_PATH.open("w", encoding="utf-8") as file:
        json.dump(manifest, file, indent=2, sort_keys=True)


def record_manifest(
    day: str,
    path: Path,
    status: str,
    error: str | None = None,
) -> dict:
    """Record download status, file metadata, and checksum."""
    entry = {
        "date": day,
        "path": str(path),
        "status": status,
        "sha256": sha256_file(path) if path.exists() else None,
        "size_bytes": path.stat().st_size if path.exists() else None,
        "error": error,
    }

    manifest = load_manifest()
    manifest[day] = entry
    save_manifest(manifest)

    return entry


def download_nse_equity_day(day: str) -> dict:
    """
    Download one NSE equity BhavCopy ZIP.

    Existing files are reused only after ZIP validation.
    Downloaded data is validated before being written.
    Invalid downloads are not saved as final ZIP files.
    """
    parsed_day = date.fromisoformat(day)

    if parsed_day.isoformat() != day:
        raise ValueError("Date must use YYYY-MM-DD format.")

    output_path = expected_zip_path(day)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Reuse a cached file only if it passes validation.
    if output_path.exists():
        try:
            validate_nse_zip(output_path.read_bytes())
        except (zipfile.BadZipFile, ValueError, OSError) as exc:
            record_manifest(
                day,
                output_path,
                "INVALID_CACHE",
                str(exc),
            )
            raise

        return record_manifest(day, output_path, "CACHED")

    url = build_bhavcopy_url(day)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Validate the response before creating the final ZIP.
        validate_nse_zip(response.content)

        # Write to a temporary file, then atomically replace the target.
        with temp_path.open("wb") as file:
            file.write(response.content)

        validate_nse_zip(temp_path.read_bytes())
        temp_path.replace(output_path)

        return record_manifest(day, output_path, "DOWNLOADED")

    except (
        requests.RequestException,
        zipfile.BadZipFile,
        ValueError,
        OSError,
    ) as exc:
        if temp_path.exists():
            temp_path.unlink()

        record_manifest(day, output_path, "ERROR", str(exc))
        raise


def date_range(start: str, end: str) -> list[str]:
    """Return every calendar date in the inclusive date range."""
    start_day = date.fromisoformat(start)
    end_day = date.fromisoformat(end)

    if end_day < start_day:
        raise ValueError("End date must be on or after start date.")

    days = []
    current = start_day

    while current <= end_day:
        days.append(current.isoformat())
        current += timedelta(days=1)

    return days


def download_nse_equity_range(
    start: str,
    end: str,
    *,
    stop_on_error: bool = False,
) -> list[dict]:
    """
    Download NSE equity BhavCopy files across an inclusive date range.

    Weekends and exchange holidays may not have files. Failures are
    recorded and returned unless stop_on_error=True.
    """
    results = []

    for day in date_range(start, end):
        try:
            result = download_nse_equity_day(day)
        except Exception as exc:
            result = {
                "date": day,
                "path": str(expected_zip_path(day)),
                "status": "ERROR",
                "sha256": None,
                "size_bytes": None,
                "error": str(exc),
            }

            results.append(result)

            if stop_on_error:
                raise

            continue

        results.append(result)

    return results
