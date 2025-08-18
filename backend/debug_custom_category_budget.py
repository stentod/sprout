#!/usr/bin/env python3
"""
Debug script to check the current state of custom category budgets.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    """Get database URL from environment"""
    return os.environ.get('DATABASE_URL')

def debug_custom_category_budget():
    """Debug custom category budget state"""
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔍 Debugging custom category budget state...")
        
        # Check custom categories
        print("\n📋 Custom Categories:")
        cursor.execute("""
            SELECT id, name, icon, color, daily_budget, user_id, created_at
            FROM custom_categories 
            ORDER BY created_at DESC
        """)
        custom_categories = cursor.fetchall()
        
        for cat in custom_categories:
            print(f"   📝 Custom Category: {cat['name']} (ID: {cat['id']}, User: {cat['user_id']})")
            print(f"      Icon: {cat['icon']}, Color: {cat['color']}")
            print(f"      Daily Budget: ${cat['daily_budget']}")
            print(f"      Created: {cat['created_at']}")
        
        # Check user category budgets
        print("\n💰 User Category Budgets:")
        cursor.execute("""
            SELECT user_id, category_id, category_type, daily_budget, created_at
            FROM user_category_budgets 
            ORDER BY created_at DESC
        """)
        user_budgets = cursor.fetchall()
        
        for budget in user_budgets:
            print(f"   💰 User {budget['user_id']}, Category {budget['category_type']}_{budget['category_id']}: ${budget['daily_budget']}")
            print(f"      Created: {budget['created_at']}")
        
        # Check expenses for custom category
        print("\n💸 Expenses for Custom Categories:")
        cursor.execute("""
            SELECT e.id, e.user_id, e.amount, e.description, e.category_id, e.timestamp
            FROM expenses e
            WHERE e.category_id LIKE 'custom_%'
            ORDER BY e.timestamp DESC
            LIMIT 10
        """)
        custom_expenses = cursor.fetchall()
        
        for expense in custom_expenses:
            print(f"   💸 Expense: ${expense['amount']} - {expense['description']}")
            print(f"      Category: {expense['category_id']}, User: {expense['user_id']}")
            print(f"      Date: {expense['timestamp']}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Debug complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_custom_category_budget()
