// Crawler Firecrawl 
// scrape business data from California Secretary of State website
// Expose business search through an API

// If the search term is /search?term=1 meaning the (term is dynamic)

// Express server setup
// Use axios
// Firecrawl package
// json2csv for converting JSON to CSV
// Include clear column names matching the field names from the site.

/* 
3. Pagination & Limits
Follow pagination until no more results.

If results exceed 500 records, stop after 500 to save time.

4. Error Handling
If any error occurs (e.g., timeout, element missing), skip that record and continue scraping.

Always save partial results to CSV and return them in the API.
*/