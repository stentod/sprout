#!/usr/bin/env python3
"""
Test script to debug add expense functionality directly without the full Flask app.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def test_add_expense():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🧪 Testing add expense functionality")
        
        # Test data
        user_id = 0  # Default user
        amount = 1.0
        description = "Test expense"
        category_id = "default_8"  # Food & Dining from the migration
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"📊 Test data:")
        print(f"   user_id: {user_id}")
        print(f"   amount: {amount}")
        print(f"   description: {description}")
        print(f"   category_id: {category_id}")
        print(f"   timestamp: {timestamp}")
        
        # Check if category exists in default_categories
        check_sql = 'SELECT id, name FROM default_categories WHERE id = %s'
        cursor.execute(check_sql, (8,))
        result = cursor.fetchone()
        if result:
            print(f"✅ Category exists: {result['id']} - {result['name']}")
        else:
            print(f"❌ Category 74 not found in default_categories")
            return
        
        # Test the actual INSERT
        sql = '''
            INSERT INTO expenses (user_id, amount, description, category_id, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        '''
        
        print(f"\n💾 Executing SQL: {sql}")
        print(f"   Parameters: ({user_id}, {amount}, '{description}', '{category_id}', '{timestamp}')")
        
        cursor.execute(sql, (user_id, amount, description, category_id, timestamp))
        result = cursor.fetchone()
        
        if result:
            expense_id = result['id']
            print(f"✅ Expense inserted successfully with ID: {expense_id}")
            conn.commit()
        else:
            print(f"❌ No result returned from INSERT")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_add_expense()
