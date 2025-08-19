#!/usr/bin/env python3
"""
Minimal deployment test to identify the issue
"""

import os
import sys

def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        import psycopg2
        print("✅ psycopg2 imported")
    except ImportError as e:
        print(f"❌ psycopg2 import failed: {e}")
        return False
    
    try:
        import flask
        print("✅ flask imported")
    except ImportError as e:
        print(f"❌ flask import failed: {e}")
        return False
    
    try:
        import bcrypt
        print("✅ bcrypt imported")
    except ImportError as e:
        print(f"❌ bcrypt import failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connection"""
    print("🧪 Testing database connection...")
    
    try:
        import psycopg2
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            print("⚠️ No DATABASE_URL found")
            return True  # Not critical for basic deployment
        
        conn = psycopg2.connect(DATABASE_URL)
        print("✅ Database connection successful")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_app_import():
    """Test if the Flask app can be imported"""
    print("🧪 Testing Flask app import...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.path.dirname(__file__))
        from app import app
        print("✅ Flask app imported successfully")
        return True
    except Exception as e:
        print(f"❌ Flask app import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔍 Deployment Test Starting...")
    print("=" * 50)
    
    success = True
    
    if not test_imports():
        success = False
    
    if not test_database_connection():
        success = False
    
    if not test_app_import():
        success = False
    
    print("=" * 50)
    if success:
        print("✅ All tests passed - deployment should work!")
        exit(0)
    else:
        print("❌ Tests failed - deployment will fail!")
        exit(1)
