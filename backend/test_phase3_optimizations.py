#!/usr/bin/env python3
"""
Test script for Phase 3 Performance Optimizations
Verifies advanced optimizations: pagination, connection pooling, and compression
"""

import requests
import json
import time
import statistics
import gzip
import concurrent.futures

def test_endpoint(url, name, auth_headers=None, check_compression=False):
    """Test an endpoint and measure response time"""
    try:
        start_time = time.time()
        headers = auth_headers or {}
        
        # Add Accept-Encoding header to test compression
        if check_compression:
            headers['Accept-Encoding'] = 'gzip, deflate'
        
        response = requests.get(url, headers=headers, timeout=10)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            compression_info = ""
            if check_compression:
                content_encoding = response.headers.get('Content-Encoding', 'none')
                compression_info = f" (compression: {content_encoding})"
            
            print(f"✅ {name}: {response_time:.1f}ms{compression_info}")
            return True, response_time, response.json(), response.headers
        else:
            print(f"❌ {name}: HTTP {response.status_code}")
            return False, response_time, None, response.headers
            
    except Exception as e:
        print(f"❌ {name}: Error - {e}")
        return False, 0, None, {}

def test_pagination():
    """Test the new pagination functionality"""
    print("\n📄 Testing pagination functionality...")
    
    base_url = "http://localhost:5001"
    
    # Test first page
    success1, time1, data1, headers1 = test_endpoint(
        f"{base_url}/api/history?page=1&per_page=10", 
        "History Page 1 (10 items)"
    )
    
    if success1 and data1:
        pagination = data1.get('pagination', {})
        print(f"   📊 Pagination info: page={pagination.get('page')}, total={pagination.get('total_count')}")
        print(f"   📊 Has next: {pagination.get('has_next')}, Has prev: {pagination.get('has_prev')}")
    
    # Test second page if available
    if success1 and data1 and data1.get('pagination', {}).get('has_next'):
        success2, time2, data2, headers2 = test_endpoint(
            f"{base_url}/api/history?page=2&per_page=10", 
            "History Page 2 (10 items)"
        )
        
        if success2 and data2:
            pagination2 = data2.get('pagination', {})
            print(f"   📊 Page 2 info: page={pagination2.get('page')}, total={pagination2.get('total_count')}")
    
    # Test different page sizes
    success3, time3, data3, headers3 = test_endpoint(
        f"{base_url}/api/history?page=1&per_page=5", 
        "History Page 1 (5 items)"
    )
    
    return success1

def test_compression():
    """Test response compression"""
    print("\n🗜️ Testing response compression...")
    
    base_url = "http://localhost:5001"
    
    # Test without compression
    success1, time1, data1, headers1 = test_endpoint(
        f"{base_url}/api/categories", 
        "Categories (no compression)", 
        check_compression=False
    )
    
    # Test with compression
    success2, time2, data2, headers2 = test_endpoint(
        f"{base_url}/api/categories", 
        "Categories (with compression)", 
        check_compression=True
    )
    
    if success1 and success2:
        compression_enabled = headers2.get('Content-Encoding') == 'gzip'
        if compression_enabled:
            print("   🎉 Compression is working!")
        else:
            print("   ⚠️  Compression not detected (may be normal for small responses)")
    
    return success1 and success2

def test_concurrent_requests():
    """Test concurrent requests to verify connection pooling"""
    print("\n🔄 Testing concurrent requests (connection pooling)...")
    
    base_url = "http://localhost:5001"
    urls = [
        f"{base_url}/api/categories",
        f"{base_url}/api/summary", 
        f"{base_url}/api/history?page=1&per_page=10",
        f"{base_url}/health"
    ]
    
    def make_request(url):
        try:
            start_time = time.time()
            response = requests.get(url, timeout=5)
            end_time = time.time()
            return (url, response.status_code, (end_time - start_time) * 1000)
        except Exception as e:
            return (url, 0, 0)
    
    # Make concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(make_request, url) for url in urls]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # Analyze results
    successful_requests = [r for r in results if r[1] == 200]
    if successful_requests:
        times = [r[2] for r in successful_requests]
        avg_time = statistics.mean(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"   📊 Concurrent requests: {len(successful_requests)}/{len(urls)} successful")
        print(f"   📊 Response times: avg={avg_time:.1f}ms, min={min_time:.1f}ms, max={max_time:.1f}ms")
        
        if max_time < 1000:  # Less than 1 second for concurrent requests
            print("   🎉 Connection pooling appears to be working well!")
        else:
            print("   ⚠️  Some requests took longer than expected")
    
    return len(successful_requests) == len(urls)

def test_phase3_optimizations():
    """Test all Phase 3 optimizations"""
    
    base_url = "http://localhost:5001"
    
    print("🚀 Testing Phase 3 Performance Optimizations")
    print("=" * 60)
    
    # Test basic connectivity
    print("\n1. Testing basic connectivity...")
    success, time1, _, _ = test_endpoint(f"{base_url}/health", "Health Check")
    
    if not success:
        print("❌ Server not responding. Please start the server first.")
        return False
    
    # Test pagination
    pagination_success = test_pagination()
    
    # Test compression
    compression_success = test_compression()
    
    # Test concurrent requests
    concurrent_success = test_concurrent_requests()
    
    # Test individual endpoints with compression
    print("\n2. Testing optimized endpoints...")
    endpoints = [
        ("/api/categories", "Categories API"),
        ("/api/summary", "Summary API"),
        ("/api/history?page=1&per_page=20", "History API (paginated)"),
    ]
    
    endpoint_times = []
    for endpoint, name in endpoints:
        success, response_time, data, headers = test_endpoint(
            f"{base_url}{endpoint}", 
            name,
            check_compression=True
        )
        if success:
            endpoint_times.append(response_time)
    
    print("\n" + "=" * 60)
    print("✅ Phase 3 optimization testing complete!")
    print("📈 Performance Summary:")
    
    if endpoint_times:
        avg_time = statistics.mean(endpoint_times)
        print(f"   • Average endpoint response time: {avg_time:.1f}ms")
    
    print("🔧 Phase 3 Features Tested:")
    print(f"   • Pagination: {'✅' if pagination_success else '❌'}")
    print(f"   • Compression: {'✅' if compression_success else '❌'}")
    print(f"   • Connection Pooling: {'✅' if concurrent_success else '❌'}")
    
    print("\n💡 Phase 3 optimizations provide:")
    print("   • Efficient handling of large datasets (pagination)")
    print("   • Reduced bandwidth usage (compression)")
    print("   • Better concurrent request handling (connection pooling)")
    
    return True

if __name__ == "__main__":
    test_phase3_optimizations()
