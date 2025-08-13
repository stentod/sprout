#!/usr/bin/env python3
"""
Debug script to test authentication endpoints locally
"""
import requests
import json

API_BASE = "http://localhost:5001"

def test_signup():
    """Test user signup"""
    print("🧪 Testing Signup...")
    
    data = {
        "username": "testuser123",
        "email": "test@example.com",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/auth/signup", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 201
    except Exception as e:
        print(f"❌ Signup failed: {e}")
        return False

def test_login(username_or_email, password):
    """Test user login"""
    print(f"🧪 Testing Login for: {username_or_email}...")
    
    data = {
        "username": username_or_email,
        "password": password
    }
    
    try:
        response = requests.post(f"{API_BASE}/api/auth/login", json=data)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            # Store session cookies for subsequent requests
            return response.cookies
        return None
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None

def test_me_endpoint(cookies):
    """Test the /me endpoint to verify session"""
    print("🧪 Testing /api/auth/me endpoint...")
    
    try:
        response = requests.get(f"{API_BASE}/api/auth/me", cookies=cookies)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ /me endpoint failed: {e}")
        return False

def test_database_connection():
    """Test basic database connectivity"""
    print("🧪 Testing Database Connection...")
    
    try:
        response = requests.get(f"{API_BASE}/api/categories")
        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Database is working (got auth error as expected)")
            return True
        elif response.status_code == 200:
            print("✅ Database is working (got response)")
            return True
        else:
            print(f"❌ Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def main():
    """Main test function"""
    print("🌱 Sprout Budget Authentication Test\n")
    
    # Test 1: Database connection
    if not test_database_connection():
        print("❌ Database connection failed. Check if server is running.")
        return
    
    print("\n" + "="*50)
    
    # Test 2: Signup (this might fail if user already exists)
    signup_success = test_signup()
    
    print("\n" + "="*50)
    
    # Test 3: Login with email
    cookies = test_login("test@example.com", "testpass123")
    
    if not cookies:
        print("\n🔄 Trying login with username...")
        cookies = test_login("testuser123", "testpass123")
    
    print("\n" + "="*50)
    
    # Test 4: Session verification
    if cookies:
        test_me_endpoint(cookies)
    else:
        print("❌ No valid session to test")
    
    print("\n" + "="*50)
    print("✅ Authentication tests completed!")
    
    if not cookies:
        print("\n💡 Recommendations:")
        print("1. Check server logs for detailed error messages")
        print("2. Verify database schema is up to date")
        print("3. Check if SECRET_KEY is properly set")
        print("4. Verify .env file configuration")

if __name__ == "__main__":
    main()
