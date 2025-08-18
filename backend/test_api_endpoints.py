#!/usr/bin/env python3
"""
Test script to check API endpoints for category preferences
"""

import os
import sys
import requests
import json

def test_api_endpoints():
    """Test the category preference API endpoints"""
    
    # Get the base URL from environment or use localhost
    base_url = os.environ.get('BASE_URL', 'http://localhost:5001')
    api_url = f"{base_url}/api"
    
    print(f"🔍 Testing API endpoints at: {api_url}")
    
    # Test GET endpoint
    print("\n📡 Testing GET /api/preferences/category-requirement")
    try:
        response = requests.get(f"{api_url}/preferences/category-requirement")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Parsed: {data}")
        else:
            print("   ❌ GET request failed")
            
    except Exception as e:
        print(f"   ❌ GET request error: {e}")
    
    # Test POST endpoint
    print("\n📡 Testing POST /api/preferences/category-requirement")
    try:
        payload = {"require_categories": False}
        response = requests.post(
            f"{api_url}/preferences/category-requirement",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Parsed: {data}")
        else:
            print("   ❌ POST request failed")
            
    except Exception as e:
        print(f"   ❌ POST request error: {e}")

if __name__ == "__main__":
    test_api_endpoints()
