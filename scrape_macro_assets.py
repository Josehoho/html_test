import csv
import io
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


STOOQ_QUOTE_URL = "https://stooq.com/q/l/"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
PROJECT_ROOT = Path.cwd() if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "macro_assets.json"
HTML_FILE = PROJECT_ROOT / "index.html"
SNAPSHOT_START = "/* MACRO_ASSETS_SNAPSHOT_START */"
SNAPSHOT_END = "/* MACRO_ASSETS_SNAPSHOT_END */"

STOOQ_ASSETS = [
    {"name": "原油（WTI期货）", "symbol": "cl.f"},
    {"name": "黄金（COMEX期货）", "symbol": "gc.f"},
    {"name": "标普500指数", "symbol": "^spx"},
]


def fetch_text(url: str, with_headers: bool = True) -> str:
    last_error = None
    for _ in range(3):
        if with_headers:
            request = Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/135.0.0.0 Safari/537.36"
                    ),
                    "Accept": "text/csv,application/json,text/plain,*/*",
                },
            )
        else:
            request = Request(url)
        try:
            with urlopen(request, timeout=12) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
            time.sleep(0.5)
    raise URLError(last_error)


def to_float(value) -> float | None:
    try:
        text = str(value).strip()
        if not text or text.upper() == "N/D":
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def fetch_stooq_asset(symbol: str, name: str) -> dict:
    url = f"{STOOQ_QUOTE_URL}?{urlencode({'s': symbol, 'f': 'sd2t2ohlcv', 'h': '', 'e': 'csv'})}"
    try:
        text = fetch_text(url)
        reader = csv.DictReader(io.StringIO(text))
        row = next(reader, None)
    except (URLError, TimeoutError, OSError):
        row = None

    if not row:
        return {
            "name": name,
            "symbol": symbol,
            "price": None,
            "change": None,
            "change_percent": None,
            "currency": "USD",
            "market_time": "",
        }

    price = to_float(row.get("Close"))
    opened = to_float(row.get("Open"))
    change = None
    change_pct = None
    if price is not None and opened is not None and opened != 0:
        change = price - opened
        change_pct = (change / opened) * 100

    date_str = str(row.get("Date", "")).strip()
    time_str = str(row.get("Time", "")).strip()
    market_time = ""
    if date_str and date_str.upper() != "N/D":
        if time_str and time_str.upper() != "N/D":
            market_time = f"{date_str}T{time_str}+00:00"
        else:
            market_time = f"{date_str}T00:00:00+00:00"

    return {
        "name": name,
        "symbol": symbol,
        "price": price,
        "change": change,
        "change_percent": change_pct,
        "currency": "USD",
        "market_time": market_time,
    }


def fetch_fred_10y_asset() -> dict:
    try:
        start_date = (datetime.now(timezone.utc).date() - timedelta(days=90)).isoformat()
        url = f"{FRED_CSV_URL}?{urlencode({'id': 'DGS10', 'cosd': start_date})}"
        text = fetch_text(url, with_headers=False)
        reader = csv.DictReader(io.StringIO(text))
        values: list[tuple[str, float]] = []
        for row in reader:
            date_str = str(row.get("observation_date", "")).strip()
            val = to_float(row.get("DGS10"))
            if date_str and val is not None:
                values.append((date_str, val))
    except (URLError, TimeoutError, OSError):
        values = []

    if not values:
        return {
            "name": "美国10年期国债收益率",
            "symbol": "DGS10",
            "price": None,
            "change": None,
            "change_percent": None,
            "currency": "PERCENT",
            "market_time": "",
        }

    last_date, last_value = values[-1]
    prev_value = values[-2][1] if len(values) > 1 else None
    change = (last_value - prev_value) if prev_value is not None else None
    change_pct = ((change / prev_value) * 100) if (change is not None and prev_value not in (None, 0)) else None

    return {
        "name": "美国10年期国债收益率",
        "symbol": "^TNX",
        "price": last_value,
        "change": change,
        "change_percent": change_pct,
        "currency": "PERCENT",
        "market_time": f"{last_date}T00:00:00+00:00",
    }


def build_payload() -> dict:
    assets = [fetch_stooq_asset(item["symbol"], item["name"]) for item in STOOQ_ASSETS]
    assets.append(fetch_fred_10y_asset())
    return {
        "target_url": "https://stooq.com/q/l/ + https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10",
        "source_mode": "stooq.quote + fred.csv",
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "assets": assets,
    }


def update_embedded_snapshot(payload: dict) -> None:
    html = HTML_FILE.read_text(encoding="utf-8")
    start = html.find(SNAPSHOT_START)
    if start == -1:
        raise RuntimeError("Cannot locate macro assets snapshot start in index.html")

    json_start = start + len(SNAPSHOT_START)
    end = html.find(SNAPSHOT_END, json_start)
    if end == -1:
        raise RuntimeError("Cannot locate macro assets snapshot end in index.html")

    snapshot_json = json.dumps(payload, ensure_ascii=False, indent=2)
    replacement = f"{SNAPSHOT_START}\nconst embeddedMacroAssets = {snapshot_json};\n    {SNAPSHOT_END}"
    updated_html = html[:start] + replacement + html[end + len(SNAPSHOT_END):]
    HTML_FILE.write_text(updated_html, encoding="utf-8")


def refresh_data(sync_html: bool = True) -> dict:
    payload = build_payload()
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if sync_html:
        update_embedded_snapshot(payload)
    return payload


def main() -> int:
    try:
        payload = refresh_data(sync_html=True)
    except HTTPError as exc:
        print(f"HTTP error: {exc.code} {exc.reason}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Network error: {exc.reason}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, RuntimeError, TimeoutError, ValueError) as exc:
        print(f"Processing error: {exc}", file=sys.stderr)
        return 1

    print(
        "Wrote "
        + str(len(payload.get("assets", [])))
        + " macro asset quote(s) to "
        + OUTPUT_FILE.name
        + ", and synced index.html"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
