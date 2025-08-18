#!/usr/bin/env python3
"""
Check if production database has been properly migrated to the new category structure.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL')

def check_production_migration():
    if not get_database_url():
        print("❌ DATABASE_URL not set - cannot check production database")
        return
    
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 Checking production database migration status")
        
        # Check if new tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('default_categories', 'custom_categories', 'user_category_budgets')
            ORDER BY table_name
        """)
        new_tables = [row['table_name'] for row in cursor.fetchall()]
        print(f"\n📋 New tables exist: {new_tables}")
        
        # Check expenses table structure
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'expenses' AND column_name = 'category_id'
        """)
        category_id_info = cursor.fetchone()
        if category_id_info:
            print(f"✅ Expenses.category_id type: {category_id_info['data_type']}")
        else:
            print("❌ Expenses.category_id column not found")
        
        # Check default categories
        cursor.execute("SELECT COUNT(*) as count FROM default_categories")
        default_count = cursor.fetchone()['count']
        print(f"📊 Default categories: {default_count}")
        
        # Check custom categories
        cursor.execute("SELECT COUNT(*) as count FROM custom_categories")
        custom_count = cursor.fetchone()['count']
        print(f"📊 Custom categories: {custom_count}")
        
        # Check user category budgets
        cursor.execute("SELECT COUNT(*) as count FROM user_category_budgets")
        budget_count = cursor.fetchone()['count']
        print(f"📊 User category budgets: {budget_count}")
        
        # Check recent expenses with category_id format
        cursor.execute("""
            SELECT category_id, COUNT(*) as count
            FROM expenses 
            WHERE category_id IS NOT NULL
            GROUP BY category_id
            ORDER BY count DESC
            LIMIT 5
        """)
        expense_formats = cursor.fetchall()
        print(f"\n💸 Recent expense category_id formats:")
        for exp in expense_formats:
            print(f"   {exp['category_id']}: {exp['count']} expenses")
        
        # Check if old categories table still exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'categories'
        """)
        old_table = cursor.fetchone()
        if old_table:
            print(f"\n⚠️ Old 'categories' table still exists")
        else:
            print(f"\n✅ Old 'categories' table has been removed")
        
        print(f"\n🎯 Migration Status Summary:")
        if len(new_tables) == 3 and category_id_info and category_id_info['data_type'] == 'character varying':
            print("✅ FULLY MIGRATED - All new tables exist and expenses table supports string category IDs")
        elif len(new_tables) == 3:
            print("⚠️ PARTIALLY MIGRATED - New tables exist but expenses table may not be updated")
        else:
            print("❌ NOT MIGRATED - New tables missing")
            
    except Exception as e:
        print(f"❌ Error checking production database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_production_migration()
