#!/usr/bin/env python3
"""
Performance Optimization Script - Phase 1
Adds database indexes to improve query performance
"""

import os
import sys
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")
    return psycopg2.connect(DATABASE_URL)

def add_performance_indexes():
    """Add performance indexes to improve query speed"""
    
    indexes = [
        # Expenses table indexes
        "CREATE INDEX IF NOT EXISTS idx_expenses_user_timestamp ON expenses(user_id, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id)",
        "CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, DATE(timestamp))",
        
        # User category budgets indexes
        "CREATE INDEX IF NOT EXISTS idx_user_category_budgets_user ON user_category_budgets(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_user_category_budgets_category ON user_category_budgets(category_id, category_type)",
        
        # Custom categories indexes
        "CREATE INDEX IF NOT EXISTS idx_custom_categories_user ON custom_categories(user_id)",
        
        # User preferences indexes
        "CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id)",
        
        # Password reset tokens indexes
        "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token)",
        "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user ON password_reset_tokens(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires ON password_reset_tokens(expires_at)"
    ]
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        print("🌱 Adding performance indexes to database...")
        
        for i, index_sql in enumerate(indexes, 1):
            try:
                print(f"  {i}/{len(indexes)}: Adding index...")
                cur.execute(index_sql)
                print(f"     ✅ Index created successfully")
            except Exception as e:
                print(f"     ⚠️  Index already exists or error: {e}")
        
        conn.commit()
        print("\n🎉 All performance indexes added successfully!")
        print("📈 These indexes will improve query performance for:")
        print("   • Loading expenses and history")
        print("   • Category management")
        print("   • User preferences")
        print("   • Authentication operations")
        
    except Exception as e:
        print(f"❌ Error adding indexes: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()
    
    return True

if __name__ == "__main__":
    print("🚀 Sprout Budget Tracker - Performance Optimization Phase 1")
    print("=" * 60)
    
    success = add_performance_indexes()
    
    if success:
        print("\n✅ Phase 1 complete! Your app should now be faster.")
        print("💡 Next: Test the app to ensure everything works correctly.")
    else:
        print("\n❌ Phase 1 failed. Check the error messages above.")
        sys.exit(1)
