#!/usr/bin/env python3
"""
Test the exact API response from the budget tracking endpoint.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone

def get_database_url():
    return os.environ.get('DATABASE_URL')

def test_api_response():
    if not get_database_url():
        print("❌ DATABASE_URL not set - cannot test production database")
        return
    
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🧪 Testing exact API response from budget tracking endpoint")
        
        user_id = 0  # Default user
        day_offset = 0  # Today
        
        # Simulate the exact API logic
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(day=today_start.day + 1)
        
        print(f"📅 Date range: {today_start} to {today_end}")
        
        # Get categories with budgets (exact API query)
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
        
        print(f"\n📋 Categories found: {len(categories)}")
        for cat in categories:
            print(f"   {cat['id']}: {cat['name']} (budget: ${cat['daily_budget']})")
        
        # Get spending data (exact API query)
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
        print(f"\n💸 Spending data:")
        for category_id, spent in spending_by_category.items():
            print(f"   {category_id}: ${spent}")
        
        # Simulate the exact API response
        budgeted_categories = []
        unbedgeted_categories = []
        total_budget = 0
        total_spent_budgeted = 0
        total_spent_unbedgeted = 0
        
        for cat in categories:
            budget = float(cat['daily_budget']) if cat['daily_budget'] else 0.0
            spent = spending_by_category.get(cat['id'], 0.0)
            
            category_data = {
                'category_id': cat['id'],
                'category_name': cat['name'],
                'category_icon': cat['icon'],
                'category_color': cat['color'],
                'spent_today': spent
            }
            
            if budget > 0:
                # This category has a budget
                remaining = budget - spent
                total_budget += budget
                total_spent_budgeted += spent
                
                category_data.update({
                    'daily_budget': budget,
                    'remaining_today': remaining,
                    'percentage_used': (spent / budget * 100),
                    'is_over_budget': spent > budget
                })
                budgeted_categories.append(category_data)
            else:
                # This category has no budget
                total_spent_unbedgeted += spent
                unbedgeted_categories.append(category_data)
        
        # Show the exact API response
        api_response = {
            'budgeted_categories': budgeted_categories,
            'unbedgeted_categories': unbedgeted_categories,
            'summary': {
                'total_budget': total_budget,
                'total_spent_budgeted': total_spent_budgeted,
                'total_spent_unbedgeted': total_spent_unbedgeted,
                'total_spent_all': total_spent_budgeted + total_spent_unbedgeted,
                'total_remaining': total_budget - total_spent_budgeted,
                'overall_percentage_used': (total_spent_budgeted / total_budget * 100) if total_budget > 0 else 0,
                'budgeted_categories_count': len(budgeted_categories),
                'unbedgeted_categories_count': len(unbedgeted_categories)
            },
            'success': True
        }
        
        print(f"\n🎯 API Response Summary:")
        print(f"   Budgeted categories: {len(budgeted_categories)}")
        print(f"   Total budget: ${total_budget}")
        print(f"   Total spent (budgeted): ${total_spent_budgeted}")
        print(f"   Total remaining: ${total_budget - total_spent_budgeted}")
        
        print(f"\n📊 Budgeted Categories Details:")
        for cat in budgeted_categories:
            print(f"   {cat['category_name']} ({cat['category_id']}):")
            print(f"     Budget: ${cat['daily_budget']}")
            print(f"     Spent: ${cat['spent_today']}")
            print(f"     Remaining: ${cat['remaining_today']}")
            print(f"     Percentage: {cat['percentage_used']:.1f}%")
            print(f"     Over budget: {cat['is_over_budget']}")
        
        print(f"\n✅ API response test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    test_api_response()
