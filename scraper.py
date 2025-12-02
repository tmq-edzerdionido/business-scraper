"""
Business scraper module for California BizFile Online
Scrapes both search results and detail pages for each business record.
"""
import asyncio
import csv
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    JsonCssExtractionStrategy,
)

# Configure logging
logger = logging.getLogger(__name__)

SEARCH_URL = "https://bizfileonline.sos.ca.gov/search/business"
MAX_RECORDS = 500

# Selectors for search page 
TABLE_ROW_SELECTOR = "table.div-table tbody tr"
SEARCH_INPUT_SELECTOR = ".search-input-wrapper input"
SEARCH_BUTTON_SELECTOR = ".search-input-wrapper button"
SEARCH_FORM_SELECTOR = ".search-input-wrapper form"


def make_search_schema():
    """Schema for extracting search results table."""
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
            {
                "name": "detailLink",
                "selector": "td:nth-child(1) a",
                "type": "attribute",
                "attribute": "href",
            },
        ],
    }


def parse_extracted_rows(extracted_content: str) -> List[Dict]:
    """Parse JSON from JsonCssExtractionStrategy."""
    if not extracted_content:
        return []

    try:
        data = json.loads(extracted_content)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("items", "rows", "BizfileSearchResults"):
                if key in data and isinstance(data[key], list):
                    return data[key]
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extracted content: {e}")
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


async def scrape_detail_page(crawler: AsyncWebCrawler, detail_url: str) -> Dict:
    """
    Scrape all fields from a business detail page.
    
    Args:
        crawler: The AsyncWebCrawler instance
        detail_url: Full URL to the detail page
    
    Returns:
        Dictionary with all detail page fields
    """
    detail_data = {}
    
    try:
        logger.info(f"Scraping detail page: {detail_url}")
        
        # Create extraction strategy for detail page
        # We'll use a generic approach to extract all visible data
        conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            page_timeout=30000,
            wait_for="css:body",  # Wait for page to load
        )
        
        result = await crawler.arun(url=detail_url, config=conf)
        
        if not result.success:
            logger.warning(f"Failed to load detail page {detail_url}: {result.error_message}")
            return detail_data
        
        # Extract data using JavaScript to get all the information
        js_extract = """
        (function() {
            const data = {};
            
            // Try to extract all label-value pairs
            const labels = document.querySelectorAll('label, .label, .field-label, dt');
            labels.forEach(label => {
                const labelText = label.textContent.trim().replace(':', '');
                let value = '';
                
                // Try to find the associated value
                if (label.nextElementSibling) {
                    value = label.nextElementSibling.textContent.trim();
                } else if (label.parentElement) {
                    const parent = label.parentElement;
                    const allText = parent.textContent.trim();
                    value = allText.replace(labelText, '').replace(':', '').trim();
                }
                
                if (labelText && value) {
                    data[labelText] = value;
                }
            });
            
            // Also try dd elements (definition lists)
            const dds = document.querySelectorAll('dd');
            const dts = document.querySelectorAll('dt');
            dts.forEach((dt, index) => {
                if (dds[index]) {
                    data[dt.textContent.trim()] = dds[index].textContent.trim();
                }
            });
            
            return JSON.stringify(data);
        })();
        """
        
        # Run the extraction
        extract_conf = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            js_code=js_extract,
            page_timeout=10000,
        )
        
        extract_result = await crawler.arun(url=detail_url, config=extract_conf)
        
        if extract_result.success and extract_result.extracted_content:
            try:
                detail_data = json.loads(extract_result.extracted_content)
            except json.JSONDecodeError:
                logger.warning(f"Could not parse detail page data for {detail_url}")
        
        # Add the detail URL for reference
        detail_data['detail_url'] = detail_url
        
    except Exception as e:
        logger.error(f"Error scraping detail page {detail_url}: {e}", exc_info=True)
    
    return detail_data


async def scrape_businesses(search_term: str, max_records: int = MAX_RECORDS) -> List[Dict]:
    """
    Main scraping function that searches for businesses and scrapes detail pages.
    
    Args:
        search_term: The search term to query
        max_records: Maximum number of records to scrape
    
    Returns:
        List of dictionaries containing all scraped data
    """
    browser_cfg = BrowserConfig(
        headless=False,  # Set to True for production
        java_script_enabled=True,
        verbose=True,
    )

    all_results = []
    errors = []

    try:
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            # Step 1: Perform search and get search results
            logger.info(f"Searching for: {search_term}")
            
            js_fill_and_submit = f"""
            (function() {{
                const input = document.querySelector("{SEARCH_INPUT_SELECTOR}");
                if (!input) throw new Error("Search input not found");

                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeInputValueSetter.call(input, {json.dumps(search_term)});

                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));

                const button = document.querySelector("{SEARCH_BUTTON_SELECTOR}");
                if (!button) throw new Error("Search button not found");

                setTimeout(() => {{
                    if (button.disabled) {{
                        button.removeAttribute('disabled');
                    }}
                    button.click();
                }}, 100);
            }})();
            """

            schema = make_search_schema()
            extraction_strategy = JsonCssExtractionStrategy(schema)

            conf = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                js_code=js_fill_and_submit,
                wait_for=f"css:{TABLE_ROW_SELECTOR}",
                extraction_strategy=extraction_strategy,
                page_timeout=60000,
            )

            result = await crawler.arun(url=SEARCH_URL, config=conf)
            
            if not result.success:
                error_msg = f"Search failed: {result.error_message}"
                logger.error(error_msg)
                errors.append(error_msg)
                # Save whatever we have and return
                write_csv(all_results, search_term, errors)
                return all_results

            # Parse search results
            search_rows = parse_extracted_rows(result.extracted_content) or []
            logger.info(f"Found {len(search_rows)} search results")

            # Dedupe and cap the results
            final_rows = dedupe_and_cap(search_rows, max_records)
            logger.info(f"Using {len(final_rows)} rows after dedupe/cap")

            # Step 2: Process search results (detail page scraping removed for speed)
            for idx, row in enumerate(final_rows):
                try:
                    # Just use search result data
                    combined_data = {
                        "search_result": row,
                    }
                    
                    all_results.append(combined_data)
                    logger.info(f"Processed {idx + 1}/{len(final_rows)}")
                    
                except Exception as e:
                    error_msg = f"Error processing record {idx + 1}: {e}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    # Continue with next record
                    continue

    except Exception as e:
        error_msg = f"Fatal error during scraping: {e}"
        logger.error(error_msg, exc_info=True)
        errors.append(error_msg)
    
    finally:
        # Always save results, even if incomplete
        write_csv(all_results, search_term, errors)
    
    return all_results


def write_csv(results: List[Dict], search_term: str, errors: List[str] = None):
    """
    Write scraped results to CSV file.
    
    Args:
        results: List of result dictionaries
        search_term: The search term used
        errors: List of error messages encountered
    """
    if not results:
        logger.warning("No results to write to CSV")
        return

    safe_name = "".join(c if c.isalnum() else "_" for c in search_term).strip("_") or "results"
    out_path = Path.cwd() / f"bizfile_{safe_name}.csv"

    DATE_COLUMNS = {"initialFilingDate"}  # set of keys that hold dates

    try:
        # Collect all unique keys from all results
        all_keys = set()
        
        # Flatten the nested structure for CSV
        flattened_results = []
        for result in results:
            flat = {}
            
            # Add search result fields
            search_data = result.get('search_result', {})
            for key, value in search_data.items():
                if key != 'detailLink':  # Skip internal link
                    flat[key] = value
            
            all_keys.update(flat.keys())
            flattened_results.append(flat)
        
        # Sort keys for consistent column order
        sorted_keys = sorted(all_keys)
        
        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=sorted_keys)
            writer.writeheader()
            
            for row in flattened_results:
                # Fill in missing keys with empty strings and apply date formatting
                complete_row = {}
                for key in sorted_keys:
                    value = row.get(key, '').strip() if row.get(key) else ''
                    
                    # Excel-friendly date wrapper
                    if key in DATE_COLUMNS and value:
                        value = f'="{value}"'
                    
                    complete_row[key] = value
                
                writer.writerow(complete_row)
        
        logger.info(f"Wrote {len(results)} rows to {out_path}")
        
        # Write errors to a separate file if any
        if errors:
            error_path = Path.cwd() / f"bizfile_{safe_name}_errors.txt"
            with error_path.open("w", encoding="utf-8") as f:
                f.write(f"Errors encountered during scraping:\n\n")
                for error in errors:
                    f.write(f"- {error}\n")
            logger.info(f"Wrote {len(errors)} errors to {error_path}")
            
    except Exception as e:
        logger.error(f"Error writing CSV: {e}", exc_info=True)
