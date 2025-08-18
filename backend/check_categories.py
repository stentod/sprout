#!/usr/bin/env python3
"""
Check what categories exist in the database.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def check_categories():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 Checking categories in database")
        
        # Check default categories
        cursor.execute("SELECT id, name FROM default_categories ORDER BY id")
        default_cats = cursor.fetchall()
        print(f"\n📋 Default categories ({len(default_cats)}):")
        for cat in default_cats:
            print(f"   default_{cat['id']}: {cat['name']}")
        
        # Check what the frontend API would return
        categories_sql = '''
            SELECT 
                'default_' || dc.id as id,
                dc.name,
                dc.icon,
                dc.color,
                COALESCE(ucb.daily_budget, 0.0) as daily_budget
            FROM default_categories dc
            LEFT JOIN user_category_budgets ucb ON ucb.category_id = dc.id 
                AND ucb.category_type = 'default' 
                AND ucb.user_id = %s
            ORDER BY name ASC
        '''
        cursor.execute(categories_sql, (0,))  # User 0
        api_cats = cursor.fetchall()
        print(f"\n🔗 API would return ({len(api_cats)}):")
        for cat in api_cats:
            print(f"   {cat['id']}: {cat['name']} (budget: ${cat['daily_budget']})")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_categories()
