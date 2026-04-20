import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


TARGET_URL = "https://polymarket.com/_next/data/build-TfctsWXpff2fKS/zh/iran.json?category=iran"
PROJECT_ROOT = Path.cwd() if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "polymarket_footer_markets.json"
HTML_FILE = PROJECT_ROOT / "index.html"
SNAPSHOT_START = "/* POLYMARKET_FOOTER_SNAPSHOT_START */"
SNAPSHOT_END = "/* POLYMARKET_FOOTER_SNAPSHOT_END */"


def fetch_json(url: str) -> dict:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="replace"))


def normalize_market_list(raw_items) -> list[dict]:
    rows: list[dict] = []
    if not isinstance(raw_items, list):
        return rows
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        slug = str(item.get("slug", "")).strip()
        if not title and not slug:
            continue
        rows.append({"title": title, "slug": slug})
    return rows


def escape_md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def build_markdown_table(newest: list[dict], popular: list[dict]) -> str:
    lines = [
        "| 分类 | 标题 | slug |",
        "|---|---|---|",
    ]
    for item in newest:
        lines.append(
            "| newestMarkets | "
            + escape_md(item["title"])
            + " | "
            + escape_md(item["slug"])
            + " |"
        )
    for item in popular:
        lines.append(
            "| popularMarkets | "
            + escape_md(item["title"])
            + " | "
            + escape_md(item["slug"])
            + " |"
        )
    return "\n".join(lines) + "\n"


def build_payload(source: dict) -> dict:
    page_props = source.get("pageProps", {}) if isinstance(source, dict) else {}
    footer_data = page_props.get("footerData", {}) if isinstance(page_props, dict) else {}

    newest = normalize_market_list(footer_data.get("newestMarkets"))
    popular = normalize_market_list(footer_data.get("popularMarkets"))
    markdown_table = build_markdown_table(newest, popular)

    return {
        "target_url": TARGET_URL,
        "source_mode": "pageProps.footerData",
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "newest_count": len(newest),
        "popular_count": len(popular),
        "newest_markets": newest,
        "popular_markets": popular,
        "markdown_table": markdown_table,
    }


def update_embedded_snapshot(payload: dict) -> None:
    html = HTML_FILE.read_text(encoding="utf-8")
    start = html.find(SNAPSHOT_START)
    if start == -1:
        raise RuntimeError("Cannot locate polymarket snapshot start in index.html")

    json_start = start + len(SNAPSHOT_START)
    end = html.find(SNAPSHOT_END, json_start)
    if end == -1:
        raise RuntimeError("Cannot locate polymarket snapshot end in index.html")

    snapshot_json = json.dumps(payload, ensure_ascii=False, indent=2)
    replacement = f"{SNAPSHOT_START}\nconst embeddedPolymarketFooter = {snapshot_json};\n    {SNAPSHOT_END}"
    updated_html = html[:start] + replacement + html[end + len(SNAPSHOT_END):]
    HTML_FILE.write_text(updated_html, encoding="utf-8")


def refresh_data(sync_html: bool = True) -> dict:
    source = fetch_json(TARGET_URL)
    payload = build_payload(source)
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
    except (json.JSONDecodeError, RuntimeError, TimeoutError) as exc:
        print(f"Processing error: {exc}", file=sys.stderr)
        return 1

    print(
        "Wrote "
        + str(payload["newest_count"])
        + " newest and "
        + str(payload["popular_count"])
        + " popular market(s) to "
        + OUTPUT_FILE.name
        + ", and synced index.html"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
