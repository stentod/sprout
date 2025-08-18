#!/usr/bin/env python3
"""
Cleanup script to remove extra default categories that were incorrectly added.
This will restore the original 7 default categories only.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def cleanup_extra_categories():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🧹 Starting cleanup: Remove extra default categories")
        
        # Check if default_categories table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'default_categories'
        """)
        
        if not cursor.fetchone():
            print("❌ default_categories table doesn't exist. Run the migration first.")
            return
        
        # Get current default categories
        cursor.execute("SELECT id, name, icon FROM default_categories ORDER BY name")
        current_categories = cursor.fetchall()
        
        print(f"📋 Current default categories ({len(current_categories)}):")
        for cat in current_categories:
            print(f"   {cat['id']}: {cat['icon']} {cat['name']}")
        
        # Define the original 7 categories that should remain
        original_categories = [
            'Food & Dining',
            'Transportation', 
            'Shopping',
            'Health & Fitness',
            'Entertainment',
            'Bills & Utilities',
            'Other'
        ]
        
        # Find categories to remove
        categories_to_remove = []
        for cat in current_categories:
            if cat['name'] not in original_categories:
                categories_to_remove.append(cat)
            elif cat['name'] in original_categories:
                # Check for duplicates
                duplicates = [c for c in current_categories if c['name'] == cat['name']]
                if len(duplicates) > 1:
                    # Keep the first one, remove the rest
                    for duplicate in duplicates[1:]:
                        if duplicate not in categories_to_remove:
                            categories_to_remove.append(duplicate)
        
        if not categories_to_remove:
            print("✅ No extra categories to remove")
            return
        
        print(f"\n🗑️ Removing {len(categories_to_remove)} extra categories:")
        for cat in categories_to_remove:
            print(f"   {cat['id']}: {cat['icon']} {cat['name']}")
        
        # Remove the extra categories
        for cat in categories_to_remove:
            cursor.execute("DELETE FROM default_categories WHERE id = %s", (cat['id'],))
            print(f"   ✅ Removed: {cat['icon']} {cat['name']}")
        
        # Verify the cleanup
        cursor.execute("SELECT id, name, icon FROM default_categories ORDER BY name")
        remaining_categories = cursor.fetchall()
        
        print(f"\n📋 Remaining default categories ({len(remaining_categories)}):")
        for cat in remaining_categories:
            print(f"   {cat['id']}: {cat['icon']} {cat['name']}")
        
        # Check for any remaining duplicates
        names = [cat['name'] for cat in remaining_categories]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        
        if duplicates:
            print(f"\n⚠️ Warning: Still have duplicates: {duplicates}")
        else:
            print("\n✅ No duplicates remaining")
        
        conn.commit()
        print("\n✅ Cleanup completed successfully!")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    cleanup_extra_categories()
