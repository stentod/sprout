#!/usr/bin/env python3
"""
Test script for Phase 1 Performance Optimizations
Verifies that the optimizations work correctly
"""

import requests
import json
import time

def test_endpoint(url, name):
    """Test an endpoint and measure response time"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=10)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            print(f"✅ {name}: {response_time:.1f}ms")
            return True, response_time
        else:
            print(f"❌ {name}: HTTP {response.status_code}")
            return False, response_time
            
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False, 0

def test_optimizations():
    """Test the optimized endpoints"""
    
    base_url = "http://localhost:5001"
    
    print("🚀 Testing Phase 1 Performance Optimizations")
    print("=" * 50)
    
    # Test basic connectivity
    print("\n1. Testing basic connectivity...")
    success, time1 = test_endpoint(f"{base_url}/health", "Health Check")
    
    if not success:
        print("❌ Server not responding. Please start the server first.")
        return False
    
    # Test categories endpoint (our main optimization)
    print("\n2. Testing categories endpoint (optimized)...")
    success, time2 = test_endpoint(f"{base_url}/api/categories", "Categories API")
    
    if success:
        print(f"   📈 Categories endpoint response time: {time2:.1f}ms")
        if time2 < 500:  # Less than 500ms is good
            print("   🎉 Excellent performance!")
        elif time2 < 1000:  # Less than 1 second is acceptable
            print("   👍 Good performance!")
        else:
            print("   ⚠️  Performance could be better")
    
    # Test other endpoints for comparison
    print("\n3. Testing other endpoints...")
    test_endpoint(f"{base_url}/", "Main Page")
    test_endpoint(f"{base_url}/api/expenses", "Expenses API")
    
    print("\n" + "=" * 50)
    print("✅ Phase 1 optimization testing complete!")
    print("💡 If all tests pass, your app is working correctly.")
    
    return True

if __name__ == "__main__":
    test_optimizations()
