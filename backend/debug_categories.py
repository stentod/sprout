#!/usr/bin/env python3
"""
Debug script to check what categories are in the database and identify duplicates.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def debug_categories():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 DEBUGGING CATEGORIES - Checking all category tables")
        
        # Check if old categories table exists and what's in it
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'categories'
        """)
        
        if cursor.fetchone():
            print("\n📋 OLD categories table exists:")
            cursor.execute("SELECT id, name, icon, is_default, user_id FROM categories ORDER BY name")
            old_categories = cursor.fetchall()
            print(f"   Found {len(old_categories)} categories in old table:")
            for cat in old_categories:
                print(f"   {cat['id']}: {cat['icon']} {cat['name']} (default: {cat['is_default']}, user: {cat['user_id']})")
        else:
            print("\n❌ OLD categories table does not exist")
        
        # Check new default_categories table
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'default_categories'
        """)
        
        if cursor.fetchone():
            print("\n📋 NEW default_categories table:")
            cursor.execute("SELECT id, name, icon FROM default_categories ORDER BY name")
            new_categories = cursor.fetchall()
            print(f"   Found {len(new_categories)} categories in new table:")
            for cat in new_categories:
                print(f"   {cat['id']}: {cat['icon']} {cat['name']}")
        else:
            print("\n❌ NEW default_categories table does not exist")
        
        # Check custom_categories table
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'custom_categories'
        """)
        
        if cursor.fetchone():
            print("\n📋 custom_categories table:")
            cursor.execute("SELECT id, name, icon, user_id FROM custom_categories ORDER BY name")
            custom_categories = cursor.fetchall()
            print(f"   Found {len(custom_categories)} custom categories:")
            for cat in custom_categories:
                print(f"   {cat['id']}: {cat['icon']} {cat['name']} (user: {cat['user_id']})")
        else:
            print("\n❌ custom_categories table does not exist")
        
        # Check for duplicates in default_categories
        if cursor.fetchone():
            cursor.execute("""
                SELECT name, COUNT(*) as count 
                FROM default_categories 
                GROUP BY name 
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            if duplicates:
                print(f"\n⚠️ DUPLICATES found in default_categories:")
                for dup in duplicates:
                    print(f"   '{dup['name']}' appears {dup['count']} times")
            else:
                print("\n✅ No duplicates in default_categories table")
        
        print("\n🔍 SUMMARY:")
        print("   - Check if the API is querying both old and new tables")
        print("   - Check if there are duplicate entries in default_categories")
        print("   - Check if frontend is caching old category data")
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        sys.exit(1)
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    debug_categories()
