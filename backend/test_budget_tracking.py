#!/usr/bin/env python3
"""
Test budget tracking API to debug why budgets aren't decreasing.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone

def get_database_url():
    return os.environ.get('DATABASE_URL')

def test_budget_tracking():
    if not get_database_url():
        print("❌ DATABASE_URL not set - cannot test production database")
        return
    
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🧪 Testing budget tracking in production")
        
        user_id = 0  # Default user
        
        # Step 1: Check what categories have budgets
        print("\n📋 Step 1: Checking categories with budgets...")
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
            
            UNION ALL
            
            SELECT 
                'custom_' || cc.id as id,
                cc.name,
                cc.icon,
                cc.color,
                COALESCE(ucb.daily_budget, cc.daily_budget, 0.0) as daily_budget
            FROM custom_categories cc
            LEFT JOIN user_category_budgets ucb ON ucb.category_id = cc.id 
                AND ucb.category_type = 'custom' 
                AND ucb.user_id = %s
            WHERE cc.user_id = %s
            
            ORDER BY name ASC
        '''
        cursor.execute(categories_sql, (user_id, user_id, user_id))
        categories = cursor.fetchall()
        
        budgeted_categories = [cat for cat in categories if cat['daily_budget'] > 0]
        print(f"   Found {len(budgeted_categories)} categories with budgets:")
        for cat in budgeted_categories:
            print(f"     {cat['name']}: ${cat['daily_budget']} (ID: {cat['id']})")
        
        if not budgeted_categories:
            print("   ❌ No categories with budgets found!")
            return
        
        # Step 2: Check today's spending
        print(f"\n💸 Step 2: Checking today's spending...")
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(day=today_start.day + 1)
        
        spending_sql = '''
            SELECT 
                CASE 
                    WHEN e.category_id LIKE 'default_%%' THEN e.category_id
                    WHEN e.category_id LIKE 'custom_%%' THEN e.category_id
                    ELSE CONCAT('default_', e.category_id)
                END as category_id,
                SUM(e.amount) as total_spent
            FROM expenses e
            WHERE e.user_id = %s AND e.timestamp >= %s AND e.timestamp < %s
            GROUP BY 
                CASE 
                    WHEN e.category_id LIKE 'default_%%' THEN e.category_id
                    WHEN e.category_id LIKE 'custom_%%' THEN e.category_id
                    ELSE CONCAT('default_', e.category_id)
                END
        '''
        cursor.execute(spending_sql, (user_id, today_start.isoformat(), today_end.isoformat()))
        spending_data = cursor.fetchall()
        
        spending_by_category = {row['category_id']: float(row['total_spent']) for row in spending_data}
        print(f"   Today's spending by category:")
        for category_id, spent in spending_by_category.items():
            print(f"     {category_id}: ${spent}")
        
        # Step 3: Calculate budget tracking manually
        print(f"\n📈 Step 3: Manual budget calculation...")
        for cat in budgeted_categories:
            budget = float(cat['daily_budget'])
            spent = spending_by_category.get(cat['id'], 0.0)
            remaining = budget - spent
            
            print(f"   {cat['name']} ({cat['id']}):")
            print(f"     Budget: ${budget}")
            print(f"     Spent: ${spent}")
            print(f"     Remaining: ${remaining}")
            print(f"     Percentage used: {(spent / budget * 100) if budget > 0 else 0}%")
        
        # Step 4: Test the exact API query
        print(f"\n🔗 Step 4: Testing exact API query...")
        try:
            # Simulate the exact query from the API
            api_categories_sql = '''
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
                
                UNION ALL
                
                SELECT 
                    'custom_' || cc.id as id,
                    cc.name,
                    cc.icon,
                    cc.color,
                    COALESCE(ucb.daily_budget, cc.daily_budget, 0.0) as daily_budget
                FROM custom_categories cc
                LEFT JOIN user_category_budgets ucb ON ucb.category_id = cc.id 
                    AND ucb.category_type = 'custom' 
                    AND ucb.user_id = %s
                WHERE cc.user_id = %s
                
                ORDER BY name ASC
            '''
            cursor.execute(api_categories_sql, (user_id, user_id, user_id))
            api_categories = cursor.fetchall()
            
            print(f"   API would return {len(api_categories)} categories:")
            for cat in api_categories:
                if cat['daily_budget'] > 0:
                    spent = spending_by_category.get(cat['id'], 0.0)
                    remaining = float(cat['daily_budget']) - spent
                    print(f"     {cat['name']}: Budget ${cat['daily_budget']}, Spent ${spent}, Remaining ${remaining}")
            
        except Exception as e:
            print(f"   ❌ API query failed: {e}")
        
        print(f"\n✅ Budget tracking test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_budget_tracking()
