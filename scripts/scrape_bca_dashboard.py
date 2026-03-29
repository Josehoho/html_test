import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


TARGET_URL = "https://www.bcaresearch.com/collection/bcas-iran-conflict-daily-dashboard"
TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
PROJECT_ROOT = Path.cwd() if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
OUTPUT_FILE = PROJECT_ROOT / "data" / "bca_dc_description.json"
HTML_FILE = PROJECT_ROOT / "index.html"
SNAPSHOT_START = "/* EMBEDDED_SNAPSHOT_START */"
SNAPSHOT_END = "/* EMBEDDED_SNAPSHOT_END */"


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class DescriptionStructureExtractor(HTMLParser):
    def __init__(self, class_name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.class_name = class_name
        self.in_target_div = False
        self.div_depth = 0
        self.current_field: str | None = None
        self.current_chunks: list[str] = []
        self.title = ""
        self.updated = ""
        self.items: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        attr_map = dict(attrs)
        classes = set((attr_map.get("class") or "").split())

        if tag == "div" and self.class_name in classes and not self.in_target_div:
            self.in_target_div = True
            self.div_depth = 1
            return

        if not self.in_target_div:
            return

        if tag == "div":
            self.div_depth += 1

        if tag == "h4":
            self._start_field("title")
        elif tag == "li":
            self._start_field("item")
        elif tag in {"p", "em"}:
            self._start_field("updated")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_target_div:
            return

        if tag == "h4" and self.current_field == "title":
            self.title = normalize_space(" ".join(self.current_chunks))
            self._clear_field()
            return

        if tag == "li" and self.current_field == "item":
            text = normalize_space(" ".join(self.current_chunks))
            if text:
                self.items.append(text)
            self._clear_field()
            return

        if tag in {"p", "em"} and self.current_field == "updated":
            text = normalize_space(" ".join(self.current_chunks))
            if text.lower().startswith("updated:"):
                self.updated = text
            self._clear_field()
            return

        if tag == "div":
            self.div_depth -= 1
            if self.div_depth == 0:
                self.in_target_div = False

    def handle_data(self, data: str) -> None:
        if self.in_target_div and self.current_field:
            cleaned = normalize_space(data)
            if cleaned:
                self.current_chunks.append(cleaned)

    def _start_field(self, field_name: str) -> None:
        self.current_field = field_name
        self.current_chunks = []

    def _clear_field(self) -> None:
        self.current_field = None
        self.current_chunks = []


def extract_fallback_structure(html: str) -> tuple[str, list[str], str]:
    title_match = re.search(r'<div[^>]*class="[^"]*\bdc-description\b[^"]*"[^>]*>.*?<h4[^>]*>(.*?)</h4>', html, re.I | re.S)
    title = normalize_space(re.sub(r"<[^>]+>", " ", title_match.group(1))) if title_match else ""

    item_matches = re.findall(
        r'<div[^>]*class="[^"]*\bdc-description\b[^"]*"[^>]*>.*?<ul>(.*?)</ul>',
        html,
        re.I | re.S,
    )
    items: list[str] = []
    if item_matches:
        for raw in re.findall(r"<li[^>]*>(.*?)</li>", item_matches[0], re.I | re.S):
            cleaned = normalize_space(re.sub(r"<[^>]+>", " ", raw))
            if cleaned:
                items.append(cleaned)

    updated_match = re.search(
        r'<div[^>]*class="[^"]*\bdc-description\b[^"]*"[^>]*>.*?<p[^>]*>\s*<em[^>]*>(.*?)</em>\s*</p>',
        html,
        re.I | re.S,
    )
    updated = normalize_space(re.sub(r"<[^>]+>", " ", updated_match.group(1))) if updated_match else ""
    return title, items, updated


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def translate_text(text: str) -> str:
    text = normalize_space(text)
    if not text:
        return ""

    query = (
        f"{TRANSLATE_URL}?client=gtx&sl=en&tl=zh-CN&dt=t&q={quote(text)}"
    )
    request = Request(
        query,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            )
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            payload = json.loads(response.read().decode(charset, errors="replace"))
        return normalize_space("".join(part[0] for part in payload[0] if part and part[0]))
    except (URLError, TimeoutError, json.JSONDecodeError, IndexError, TypeError):
        return ""


def build_payload(title: str, items: list[str], updated: str, source_mode: str) -> dict:
    title_zh = translate_text(title) if title else ""
    updated_zh = translate_text(updated) if updated else ""
    translated_items = [
        {
            "index": idx + 1,
            "text": text,
            "text_zh": translate_text(text),
        }
        for idx, text in enumerate(items)
    ]
    return {
        "target_url": TARGET_URL,
        "selector": "div.dc-description",
        "source_mode": source_mode,
        "fetched_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "title": title,
        "title_zh": title_zh,
        "updated": updated,
        "updated_zh": updated_zh,
        "item_count": len(items),
        "items": translated_items,
    }


def update_embedded_snapshot(payload: dict) -> None:
    html = HTML_FILE.read_text(encoding="utf-8")
    start = html.find(SNAPSHOT_START)
    if start == -1:
        raise RuntimeError("Cannot locate embedded snapshot start in index.html")

    json_start = start + len(SNAPSHOT_START)
    end = html.find(SNAPSHOT_END, json_start)
    if end == -1:
        raise RuntimeError("Cannot locate embedded snapshot end in index.html")

    snapshot_json = json.dumps(payload, ensure_ascii=False, indent=2)
    replacement = f"{SNAPSHOT_START}\nconst embeddedSnapshot = {snapshot_json};\n    {SNAPSHOT_END}"
    updated_html = html[:start] + replacement + html[end + len(SNAPSHOT_END):]
    HTML_FILE.write_text(updated_html, encoding="utf-8")


def refresh_data(sync_html: bool = True) -> dict:
    html = fetch_html(TARGET_URL)

    extractor = DescriptionStructureExtractor("dc-description")
    extractor.feed(html)
    extractor.close()

    title = extractor.title
    items = extractor.items
    updated = extractor.updated
    source_mode = "div.dc-description-structured"

    if not items:
        title, items, updated = extract_fallback_structure(html)
        source_mode = "fallback-structured"

    payload = build_payload(title, items, updated, source_mode)
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

    print(
        f"Wrote {payload['item_count']} item(s) to {OUTPUT_FILE.name} and synced index.html using mode: {payload['source_mode']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
