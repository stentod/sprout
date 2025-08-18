#!/usr/bin/env python3
"""
Force cleanup script to completely reset default categories to original 7.
This will delete ALL default categories and recreate only the original 7.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def force_cleanup_categories():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🧹 FORCE CLEANUP: Reset default categories to original 7")
        
        # Check if default_categories table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'default_categories'
        """)
        
        if not cursor.fetchone():
            print("❌ default_categories table doesn't exist. Run the migration first.")
            return
        
        # Get current count
        cursor.execute("SELECT COUNT(*) as count FROM default_categories")
        current_count = cursor.fetchone()['count']
        print(f"📊 Current default categories: {current_count}")
        
        if current_count > 0:
            # Show what we're about to delete
            cursor.execute("SELECT id, name, icon FROM default_categories ORDER BY name")
            current_categories = cursor.fetchall()
            print(f"\n🗑️ DELETING ALL current default categories:")
            for cat in current_categories:
                print(f"   {cat['id']}: {cat['icon']} {cat['name']}")
            
            # Delete ALL default categories
            cursor.execute("DELETE FROM default_categories")
            deleted_count = cursor.rowcount
            print(f"\n✅ Deleted {deleted_count} categories")
        
        # Insert ONLY the original 7 categories
        print("\n📝 INSERTING original 7 categories:")
        original_categories = [
            ('Food & Dining', '🍽️', '#FF6B6B'),
            ('Transportation', '🚗', '#4ECDC4'),
            ('Shopping', '🛒', '#45B7D1'),
            ('Health & Fitness', '💪', '#96CEB4'),
            ('Entertainment', '🎬', '#FECA57'),
            ('Bills & Utilities', '⚡', '#FF9FF3'),
            ('Other', '📝', '#6B7280')
        ]
        
        for name, icon, color in original_categories:
            cursor.execute("""
                INSERT INTO default_categories (name, icon, color)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (name, icon, color))
            new_id = cursor.fetchone()['id']
            print(f"   ✅ {new_id}: {icon} {name}")
        
        # Verify the result
        cursor.execute("SELECT id, name, icon FROM default_categories ORDER BY name")
        final_categories = cursor.fetchall()
        
        print(f"\n📋 FINAL default categories ({len(final_categories)}):")
        for cat in final_categories:
            print(f"   {cat['id']}: {cat['icon']} {cat['name']}")
        
        # Check for duplicates
        names = [cat['name'] for cat in final_categories]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        
        if duplicates:
            print(f"\n⚠️ WARNING: Still have duplicates: {duplicates}")
        else:
            print("\n✅ No duplicates - cleanup successful!")
        
        conn.commit()
        print("\n🎉 FORCE CLEANUP COMPLETED!")
        print("   Your app now has exactly 7 default categories (no duplicates)")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Force cleanup failed: {e}")
        sys.exit(1)
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    force_cleanup_categories()
