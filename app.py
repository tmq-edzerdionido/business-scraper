from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
from scraper import scrape_businesses
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

MAX_RECORDS = 500


@app.route('/search', methods=['GET'])
def search():
    """
    Search endpoint that accepts a search term and returns scraped business data.
    
    Query Parameters:
        term (str): The search term to query
        max_records (int, optional): Maximum number of records to return (default: 500)
    
    Returns:
        JSON response with:
        - success: boolean
        - data: list of business records
        - count: number of records returned
        - csv_file: path to the generated CSV file
        - message: any error or status messages
    """
    search_term = request.args.get('term', '').strip()
    
    if not search_term:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: term',
            'message': 'Please provide a search term using ?term=YOUR_SEARCH'
        }), 400
    
    try:
        max_records = int(request.args.get('max_records', MAX_RECORDS))
    except ValueError:
        max_records = MAX_RECORDS
    
    logger.info(f"Received search request for term: '{search_term}' (max: {max_records})")
    
    try:
        # Run the async scraper
        results = asyncio.run(scrape_businesses(search_term, max_records))
        
        # Generate CSV filename
        safe_name = "".join(c if c.isalnum() else "_" for c in search_term).strip("_") or "results"
        csv_file = f"bizfile_{safe_name}.csv"
        
        response_data = {
            'success': True,
            'data': results,
            'count': len(results),
            'csv_file': csv_file,
            'search_term': search_term,
            'message': f'Successfully scraped {len(results)} records'
        }
        
        logger.info(f"Search completed: {len(results)} records returned")
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error during scraping: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'An error occurred during scraping. Check server logs for details.'
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Business Scraper API'
    }), 200


@app.route('/', methods=['GET'])
def index():
    """API documentation endpoint"""
    return jsonify({
        'name': 'Business Scraper API',
        'version': '1.0',
        'endpoints': {
            '/search': {
                'method': 'GET',
                'description': 'Search for businesses and scrape data',
                'parameters': {
                    'term': 'Search term (required)',
                    'max_records': 'Maximum records to return (optional, default: 500)'
                },
                'example': '/search?term=ACME'
            },
            '/health': {
                'method': 'GET',
                'description': 'Health check endpoint'
            }
        }
    }), 200


if __name__ == '__main__':
    # Development server
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
