#!/usr/bin/env python3
"""
Simple test client for the Business Scraper API
Usage: python test_api.py [search_term]
"""
import requests
import sys
import json


def test_api(search_term: str = "ACME", max_records: int = 10):
    """Test the scraper API with a search term."""
    base_url = "http://localhost:5000"
    
    print(f"\n{'='*60}")
    print(f"Testing Business Scraper API")
    print(f"{'='*60}\n")
    
    # Test 1: Health check
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
    except requests.exceptions.ConnectionError:
        print("   ERROR: Could not connect to API. Is the server running?")
        print("   Start the server with: python app.py\n")
        return
    except Exception as e:
        print(f"   ERROR: {e}\n")
        return
    
    # Test 2: Root endpoint (documentation)
    print("2. Testing documentation endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Available endpoints: {list(data.get('endpoints', {}).keys())}\n")
    except Exception as e:
        print(f"   ERROR: {e}\n")
    
    # Test 3: Search endpoint
    print(f"3. Testing search endpoint with term='{search_term}'...")
    print(f"   (This may take a while as it scrapes the website)\n")
    
    try:
        response = requests.get(
            f"{base_url}/search",
            params={"term": search_term, "max_records": max_records}
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Success: {data.get('success')}")
            print(f"   Records found: {data.get('count')}")
            print(f"   CSV file: {data.get('csv_file')}")
            print(f"   Message: {data.get('message')}\n")
            
            # Show first result if available
            if data.get('data') and len(data['data']) > 0:
                print("   First result preview:")
                first_result = data['data'][0]
                
                # Show search result data
                if 'search_result' in first_result:
                    print("   \n   Search Result Fields:")
                    for key, value in first_result['search_result'].items():
                        if key != 'detailLink':
                            print(f"     - {key}: {value}")
                
                # Show detail page data (first few fields)
                if 'detail_page' in first_result:
                    print("   \n   Detail Page Fields (sample):")
                    detail_fields = list(first_result['detail_page'].items())[:5]
                    for key, value in detail_fields:
                        print(f"     - {key}: {value}")
                    if len(first_result['detail_page']) > 5:
                        print(f"     ... and {len(first_result['detail_page']) - 5} more fields")
                
                print()
        else:
            print(f"   Error: {response.json()}\n")
            
    except Exception as e:
        print(f"   ERROR: {e}\n")
    
    # Test 4: Invalid request (missing term)
    print("4. Testing error handling (missing required parameter)...")
    try:
        response = requests.get(f"{base_url}/search")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}\n")
    except Exception as e:
        print(f"   ERROR: {e}\n")
    
    print(f"{'='*60}")
    print("Testing complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    search_term = sys.argv[1] if len(sys.argv) > 1 else "ACME"
    max_records = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    test_api(search_term, max_records)
