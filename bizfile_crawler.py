import asyncio
import csv
import json
import sys
from pathlib import Path

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    JsonCssExtractionStrategy,
)

SEARCH_URL = "https://bizfileonline.sos.ca.gov/search/business"
MAX_RECORDS = 500

# ====== YOUR SELECTORS (these look reasonable, but verify in DevTools) ======
# 1) Table row selector for search results
TABLE_ROW_SELECTOR = "table.div-table tbody tr"

# 2) Search input + button on the initial page
SEARCH_INPUT_SELECTOR = ".search-input-wrapper input"
SEARCH_BUTTON_SELECTOR = ".search-input-wrapper button"

SEARCH_FORM_SELECTOR =".search-input-wrapper form"
# ===========================================================================

# CSV column definition – headers should match what the site shows
CSV_COLUMNS = [
    ("entityInformation", "Entity Information"),
    ("initialFilingDate", "Initial Filing Date"),
    ("status", "Status"),
    ("entityType", "Entity Type"),
    ("formedIn", "Formed In"),
    ("agent", "Agent"),
]


def make_schema():
    """
    Schema for JsonCssExtractionStrategy.

    It extracts each table row with columns mapped to our internal keys.
    """
    return {
        "name": "BizfileSearchResults",
        "baseSelector": TABLE_ROW_SELECTOR,
        "fields": [
            {
                "name": "entityInformation",
                "selector": "td:nth-child(1)",
                "type": "text",
            },
            {
                "name": "initialFilingDate",
                "selector": "td:nth-child(2)",
                "type": "text",
            },
            {
                "name": "status",
                "selector": "td:nth-child(3)",
                "type": "text",
            },
            {
                "name": "entityType",
                "selector": "td:nth-child(4)",
                "type": "text",
            },
            {
                "name": "formedIn",
                "selector": "td:nth-child(5)",
                "type": "text",
            },
            {
                "name": "agent",
                "selector": "td:nth-child(6)",
                "type": "text",
            },
        ],
    }


def parse_extracted_rows(extracted_content: str):
    """
    Handle whatever JSON shape JsonCssExtractionStrategy gives back.
    Usually it's {"items": [ ... ]} or a raw list.
    """
    if not extracted_content:
        return []

    data = json.loads(extracted_content)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Common shapes; adapt if your logs show different
        for key in ("items", "rows", "BizfileSearchResults"):
            if key in data and isinstance(data[key], list):
                return data[key]
    return []


def dedupe_and_cap(rows, max_records):
    """
    Optional: dedupe by entityInformation and cap at max_records.
    """
    seen = set()
    cleaned = []

    for row in rows:
        entity_information = (row.get("entityInformation") or "").strip()
        if not entity_information:
            continue
        if entity_information in seen:
            continue
        seen.add(entity_information)
        cleaned.append(row)
        if len(cleaned) >= max_records:
            break

    return cleaned


async def crawl_bizfile(search_term: str, max_records: int = MAX_RECORDS):
    browser_cfg = BrowserConfig(
        headless=False,
        java_script_enabled=True,
        verbose=True,
    )

    schema = make_schema()
    extraction_strategy = JsonCssExtractionStrategy(schema)

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # ---------- Single page: open, fill search, click button ----------
        js_fill_and_submit = f"""
        (function() {{
            const input = document.querySelector("{SEARCH_INPUT_SELECTOR}");
            if (!input) throw new Error("Search input not found: {SEARCH_INPUT_SELECTOR}");

            // Use the native value setter so frameworks (like React) see the change
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            nativeInputValueSetter.call(input, {json.dumps(search_term)});

            // Fire the events the framework is likely listening for
            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));

            const button = document.querySelector("{SEARCH_BUTTON_SELECTOR}");
            if (!button) throw new Error("Search button not found: {SEARCH_BUTTON_SELECTOR}");

            // Give any debounce/validation a tick to run, then click
            setTimeout(() => {{
                // If they still keep it disabled, we can force-enable as a last resort
                if (button.disabled) {{
                    button.removeAttribute('disabled');
                }}
                button.click();
            }}, 0);
        }})();
        """


        conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_fill_and_submit,
            # Wait until at least one result row appears
            wait_for=f"css:{TABLE_ROW_SELECTOR}",
            extraction_strategy=extraction_strategy,
            page_timeout=60000,
        )

        result = await crawler.arun(url=SEARCH_URL, config=conf)
        if not result.success:
            raise RuntimeError(f"Search failed: {result.error_message}")

        # Debug once if needed:
        # print("RAW EXTRACTED:", result.extracted_content)

        page_rows = parse_extracted_rows(result.extracted_content) or []
        print(f"Got {len(page_rows)} raw rows from page")

        final_rows = dedupe_and_cap(page_rows, max_records)
        print(f"Using {len(final_rows)} rows after dedupe/cap")

        return final_rows


def write_csv(rows, search_term: str):
    if not rows:
        print("No rows to write.")
        return

    safe_name = "".join(c if c.isalnum() else "_" for c in search_term).strip("_") or "results"
    out_path = Path.cwd() / f"bizfile_{safe_name}.csv"

    DATE_COLUMNS = {"initialFilingDate"}  # set of keys that hold dates

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header row
        writer.writerow([header for _, header in CSV_COLUMNS])

        for row in rows:
            formatted_row = []
            for key, _ in CSV_COLUMNS:
                value = (row.get(key) or "").strip()

                # Excel-friendly date wrapper
                if key in DATE_COLUMNS and value:
                    value = f'="{value}"'

                formatted_row.append(value)

            writer.writerow(formatted_row)

    print(f"Wrote {len(rows)} rows to {out_path}")



async def main():
    if len(sys.argv) < 2:
        print("Usage: python bizfile_crawl4ai.py \"SEARCH TERM\"")
        sys.exit(1)

    search_term = " ".join(sys.argv[1:]).strip()
    print(f"Searching for: {search_term!r} (max {MAX_RECORDS} records)")

    rows = await crawl_bizfile(search_term, MAX_RECORDS)
    print(f"\nTotal unique rows collected: {len(rows)}")
    write_csv(rows, search_term)


if __name__ == "__main__":
    asyncio.run(main())
