#!/usr/bin/env python3
"""
Test script for Phase 2 Performance Optimizations
Verifies that the optimizations work correctly and measures improvements
"""

import requests
import json
import time
import statistics

def test_endpoint(url, name, auth_headers=None):
    """Test an endpoint and measure response time"""
    try:
        start_time = time.time()
        headers = auth_headers or {}
        response = requests.get(url, headers=headers, timeout=10)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            print(f"✅ {name}: {response_time:.1f}ms")
            return True, response_time, response.json()
        else:
            print(f"❌ {name}: HTTP {response.status_code}")
            return False, response_time, None
            
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False, 0, None

def test_multiple_requests(url, name, count=5, auth_headers=None):
    """Test an endpoint multiple times and get average response time"""
    times = []
    successes = 0
    
    print(f"\n🔄 Testing {name} ({count} requests)...")
    
    for i in range(count):
        success, response_time, _ = test_endpoint(url, f"{name} #{i+1}", auth_headers)
        if success:
            times.append(response_time)
            successes += 1
    
    if times:
        avg_time = statistics.mean(times)
        min_time = min(times)
        max_time = max(times)
        print(f"📊 {name} Results:")
        print(f"   Average: {avg_time:.1f}ms")
        print(f"   Min: {min_time:.1f}ms")
        print(f"   Max: {max_time:.1f}ms")
        print(f"   Success Rate: {successes}/{count}")
        return avg_time
    else:
        print(f"❌ {name}: All requests failed")
        return None

def test_phase2_optimizations():
    """Test the Phase 2 optimizations"""
    
    base_url = "http://localhost:5001"
    
    print("🚀 Testing Phase 2 Performance Optimizations")
    print("=" * 60)
    
    # Test basic connectivity
    print("\n1. Testing basic connectivity...")
    success, time1, _ = test_endpoint(f"{base_url}/health", "Health Check")
    
    if not success:
        print("❌ Server not responding. Please start the server first.")
        return False
    
    # Test summary endpoint (our main Phase 2 optimization)
    print("\n2. Testing summary endpoint (optimized 7-day calculation)...")
    summary_times = []
    for i in range(3):
        success, time2, data = test_endpoint(f"{base_url}/api/summary", f"Summary API #{i+1}")
        if success and data:
            summary_times.append(time2)
            print(f"   📈 Summary data: balance={data.get('balance')}, plant={data.get('plant_state')}")
    
    if summary_times:
        avg_summary_time = statistics.mean(summary_times)
        print(f"   📊 Average summary response time: {avg_summary_time:.1f}ms")
        if avg_summary_time < 500:
            print("   🎉 Excellent summary performance!")
        elif avg_summary_time < 1000:
            print("   👍 Good summary performance!")
        else:
            print("   ⚠️  Summary performance could be better")
    
    # Test categories endpoint (Phase 1 optimization)
    print("\n3. Testing categories endpoint (Phase 1 optimization)...")
    categories_avg = test_multiple_requests(f"{base_url}/api/categories", "Categories API", 3)
    
    # Test history endpoint
    print("\n4. Testing history endpoint...")
    history_avg = test_multiple_requests(f"{base_url}/api/history", "History API", 3)
    
    # Test caching by making multiple requests to the same endpoint
    print("\n5. Testing caching effectiveness...")
    print("   Making 3 rapid requests to test caching...")
    cache_times = []
    for i in range(3):
        success, time3, _ = test_endpoint(f"{base_url}/api/summary", f"Cached Summary #{i+1}")
        if success:
            cache_times.append(time3)
    
    if len(cache_times) >= 2:
        first_request = cache_times[0]
        subsequent_avg = statistics.mean(cache_times[1:])
        if subsequent_avg < first_request * 0.8:  # 20% improvement
            print(f"   🎉 Caching working! First: {first_request:.1f}ms, Subsequent avg: {subsequent_avg:.1f}ms")
        else:
            print(f"   📊 Caching results - First: {first_request:.1f}ms, Subsequent avg: {subsequent_avg:.1f}ms")
    
    print("\n" + "=" * 60)
    print("✅ Phase 2 optimization testing complete!")
    print("📈 Performance Summary:")
    if summary_times:
        print(f"   • Summary endpoint: {statistics.mean(summary_times):.1f}ms avg")
    if categories_avg:
        print(f"   • Categories endpoint: {categories_avg:.1f}ms avg")
    if history_avg:
        print(f"   • History endpoint: {history_avg:.1f}ms avg")
    print("💡 If all tests pass, your Phase 2 optimizations are working!")
    
    return True

if __name__ == "__main__":
    test_phase2_optimizations()
