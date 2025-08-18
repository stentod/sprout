#!/usr/bin/env python3
"""
Test script to check category preference functionality
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    """Get database URL from environment variable"""
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def test_database_schema():
    """Test if the require_categories column exists"""
    conn = None
    try:
        # Connect to database
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 Testing database schema...")
        
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_preferences' 
            AND column_name = 'require_categories'
        """)
        
        result = cursor.fetchone()
        if result:
            print("✅ Column 'require_categories' exists in user_preferences table")
        else:
            print("❌ Column 'require_categories' does NOT exist in user_preferences table")
            print("   This is likely the cause of the error!")
            return False
        
        # Check table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'user_preferences'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print("\n📋 user_preferences table structure:")
        for col in columns:
            print(f"   {col['column_name']}: {col['data_type']} (nullable: {col['is_nullable']}, default: {col['column_default']})")
        
        # Test inserting a preference
        cursor.execute("""
            INSERT INTO user_preferences (user_id, require_categories)
            VALUES (0, TRUE)
            ON CONFLICT (user_id) DO UPDATE SET
                require_categories = EXCLUDED.require_categories,
                updated_at = CURRENT_TIMESTAMP
            RETURNING user_id, require_categories
        """)
        
        result = cursor.fetchone()
        if result:
            print(f"✅ Test insert/update successful: user_id={result['user_id']}, require_categories={result['require_categories']}")
        else:
            print("❌ Test insert/update failed")
            return False
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = test_database_schema()
    if success:
        print("\n✅ Database schema test passed!")
    else:
        print("\n❌ Database schema test failed!")
        print("   You may need to run the migration script:")
        print("   python3 backend/migrate_category_preference.py")
