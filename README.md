# Business Scraper API

A Flask-based REST API that scrapes business data from California BizFile Online, including both search results and detailed business information from individual detail pages.

## Features

- ✅ **REST API** with `/search` endpoint accepting search terms
- ✅ **Complete data scraping**: Extracts all fields from both search results and detail pages
- ✅ **JSON response**: Returns structured data in JSON format
- ✅ **CSV export**: Automatically saves results to CSV files
- ✅ **Error handling**: Skips failed records and continues scraping
- ✅ **Pagination handling**: Processes up to 500 records (configurable)
- ✅ **Partial results**: Always saves and returns whatever data was successfully scraped

## Requirements

- Python 3.8+
- Chrome/Chromium browser (for crawl4ai)

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd /home/edsaur/assessment-dtf/business-scraper
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install crawl4ai (if not already installed):**
   ```bash
   crawl4ai-setup
   ```

## Usage

### Starting the API Server

```bash
python app.py
```

The server will start on `http://localhost:5000`

### API Endpoints

#### 1. Root Endpoint (API Documentation)
```bash
GET http://localhost:5000/
```

Returns API documentation and available endpoints.

#### 2. Health Check
```bash
GET http://localhost:5000/health
```

Returns the health status of the API.

#### 3. Search Endpoint (Main Feature)
```bash
GET http://localhost:5000/search?term=ACME
```

**Query Parameters:**
- `term` (required): The search term to query
- `max_records` (optional): Maximum number of records to return (default: 500)

**Example Requests:**
```bash
# Search for "ACME"
curl "http://localhost:5000/search?term=ACME"

# Search with custom max records
curl "http://localhost:5000/search?term=Tesla&max_records=100"

# Using httpie
http GET "http://localhost:5000/search?term=ACME"
```

**Response Format:**
```json
{
  "success": true,
  "data": [
    {
      "search_result": {
        "entityInformation": "ACME CORPORATION",
        "initialFilingDate": "01/15/2020",
        "status": "ACTIVE",
        "entityType": "DOMESTIC STOCK",
        "formedIn": "CA",
        "agent": "JOHN DOE"
      },
      "detail_page": {
        "Entity Number": "C1234567",
        "Entity Name": "ACME CORPORATION",
        "Registration Date": "01/15/2020",
        "Jurisdiction": "CALIFORNIA",
        "Agent Name": "JOHN DOE",
        "Agent Address": "123 Main St, Los Angeles, CA 90001",
        "detail_url": "https://bizfileonline.sos.ca.gov/..."
      }
    }
  ],
  "count": 1,
  "csv_file": "bizfile_ACME.csv",
  "search_term": "ACME",
  "message": "Successfully scraped 1 records"
}
```

### CSV Output

Every search automatically generates a CSV file in the project directory:
- **Filename format**: `bizfile_{search_term}.csv`
- **Contains**: All scraped fields from both search results and detail pages
- **Columns**: Prefixed with `search_` or `detail_` for clarity

**Example**: Searching for "ACME" creates `bizfile_ACME.csv`

### Error Handling

The API includes comprehensive error handling:

1. **Individual record failures**: Skips the failed record, logs the error, and continues with the next one
2. **Partial results**: Always saves whatever data was successfully scraped before an error occurred
3. **Error logging**: Creates an `_errors.txt` file with details of any errors encountered
4. **HTTP error responses**: Returns appropriate status codes (400 for bad requests, 500 for server errors)

**Example error response:**
```json
{
  "success": false,
  "error": "Missing required parameter: term",
  "message": "Please provide a search term using ?term=YOUR_SEARCH"
}
```

## Project Structure

```
business-scraper/
├── app.py                 # Flask API server
├── scraper.py            # Core scraping logic
├── bizfile_crawler.py    # Original standalone script (deprecated)
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── bizfile_*.csv        # Generated CSV files
└── bizfile_*_errors.txt # Error logs (if errors occurred)
```

## Architecture

### `app.py` - Flask API Server
- Defines REST endpoints
- Handles request validation
- Runs the async scraper
- Returns JSON responses
- Includes CORS support for frontend integration

### `scraper.py` - Scraping Engine
- **Search phase**: Submits search term and extracts table results
- **Detail phase**: Visits each business detail page and extracts all fields
- **Error handling**: Try-catch blocks around each record
- **CSV generation**: Flattens nested data structure for CSV export
- **Logging**: Comprehensive logging for debugging

## Development

### Running in Debug Mode

The Flask app runs in debug mode by default (configured in `app.py`):
```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

### Testing

```bash
# Test with curl
curl -X GET "http://localhost:5000/search?term=Test"

# Test with Python requests
python -c "import requests; print(requests.get('http://localhost:5000/search?term=ACME').json())"
```

### Logging

Logs are printed to console with timestamps. Example output:
```
2025-12-02 10:30:15 - scraper - INFO - Searching for: ACME
2025-12-02 10:30:18 - scraper - INFO - Found 25 search results
2025-12-02 10:30:20 - scraper - INFO - Scraped 1/25
2025-12-02 10:30:22 - scraper - INFO - Scraped 2/25
...
```

## Configuration

### Maximum Records
Adjust in `scraper.py`:
```python
MAX_RECORDS = 500  # Change to desired limit
```

### Headless Mode
For production, set headless mode in `scraper.py`:
```python
browser_cfg = BrowserConfig(
    headless=True,  # Set to True for production
    java_script_enabled=True,
    verbose=True,
)
```

### Timeout Settings
Adjust timeouts in `scraper.py`:
```python
page_timeout=60000,  # 60 seconds for search page
page_timeout=30000,  # 30 seconds for detail pages
```

## Limitations & Notes

1. **Rate limiting**: Includes 0.5s delay between detail page requests to be respectful
2. **Browser required**: Uses crawl4ai which requires Chrome/Chromium
3. **JavaScript required**: The site is JavaScript-heavy, so JavaScript must be enabled
4. **No pagination**: The target website doesn't appear to have pagination (all results on one page)
5. **500 record limit**: Default limit to prevent excessive scraping time

## Troubleshooting

### "Search input not found" error
- The website structure may have changed
- Update selectors in `scraper.py`

### Browser not launching
- Run `crawl4ai-setup` to install browser dependencies
- Check that Chrome/Chromium is installed

### CSV file empty
- Check the error log file (`bizfile_*_errors.txt`)
- Review console logs for specific errors
- Verify the search term returns results on the actual website

### Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Activate your virtual environment if using one

## License

MIT License - feel free to use and modify as needed.
