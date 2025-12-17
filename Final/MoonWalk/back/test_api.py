#!/usr/bin/env python
"""
Test script to send mock queries to the Flask API backend.
Run this while the Flask server is running: python -m back.back
Then in another terminal: python back/test_api.py
"""

import requests
import json
import argparse

BASE_URL = "http://localhost:5000"

def test_health():
    """Test the health check endpoint"""
    print("\n=== Testing Health Check ===")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to Flask server. Make sure it's running!")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_query(query_text):
    """Test the query endpoint with a sample query"""
    print(f"\n=== Testing Query Endpoint ===")
    print(f"Query: {query_text}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/query",
            json={"query": query_text},
            headers={"Content-Type": "application/json"}
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response:")
        print(json.dumps(result, indent=2))
        return result
    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to Flask server. Make sure it's running!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the Flask API")
    parser.add_argument(
        "--query",
        type=str,
        default="a person walking in the park",
        help="Text query to send to the API"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Only test health check endpoint"
    )
    
    args = parser.parse_args()
    
    if args.health:
        test_health()
    else:
        test_health()
        test_query(args.query)
