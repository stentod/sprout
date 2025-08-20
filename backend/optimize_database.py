#!/usr/bin/env python3
"""
Database Optimization Script for Sprout Budget Tracker

This script adds strategic indexes to improve query performance without affecting
any existing functionality. All indexes are created with IF NOT EXISTS to ensure
safe, repeatable execution.

Performance improvements:
- Faster user authentication queries
- Faster expense lookups by user and date
- Faster category queries
- Better performance for budget tracking
- Optimized password reset token lookups
"""

import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")

def get_db_connection():
    """Get a database connection"""
    return psycopg2.connect(DATABASE_URL)

def run_optimization():
    """Run database optimization"""
    print("🚀 Sprout Budget Tracker - Database Optimization")
    print("=" * 60)
    print("Adding strategic indexes for better performance...")
    print("⚠️  This will NOT affect any existing functionality")
    print()
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ==========================================
        # USERS TABLE OPTIMIZATION
        # ==========================================
        print("📋 Optimizing users table...")
        
        # Index on email for fast login lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email 
            ON users(email)
        """)
        print("   ✅ Email index for fast login queries")
        
        # Index on created_at for user analytics
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_created_at 
            ON users(created_at)
        """)
        print("   ✅ Created_at index for user analytics")
        
        # ==========================================
        # EXPENSES TABLE OPTIMIZATION
        # ==========================================
        print("\n📋 Optimizing expenses table...")
        
        # Composite index for user expenses (most common query)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_user_timestamp 
            ON expenses(user_id, timestamp DESC)
        """)
        print("   ✅ User + timestamp index for expense history")
        
        # Index on user_id for user-specific queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_user_id 
            ON expenses(user_id)
        """)
        print("   ✅ User_id index for user expense queries")
        
        # Index on timestamp for date-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_timestamp 
            ON expenses(timestamp DESC)
        """)
        print("   ✅ Timestamp index for date-based queries")
        
        # Index on category_id for category-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_category_id 
            ON expenses(category_id)
        """)
        print("   ✅ Category_id index for category-based queries")
        
        # Composite index for daily spending calculations
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_expenses_user_date 
            ON expenses(user_id, DATE(timestamp))
        """)
        print("   ✅ User + date index for daily budget calculations")
        
        # ==========================================
        # PASSWORD RESET TOKENS OPTIMIZATION
        # ==========================================
        print("\n📋 Optimizing password reset tokens...")
        
        # Index on token for fast token validation
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reset_tokens_token 
            ON password_reset_tokens(token)
        """)
        print("   ✅ Token index for fast validation")
        
        # Index on expires_at for cleanup queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reset_tokens_expires 
            ON password_reset_tokens(expires_at)
        """)
        print("   ✅ Expires_at index for cleanup operations")
        
        # Composite index for user token lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reset_tokens_user_expires 
            ON password_reset_tokens(user_id, expires_at)
        """)
        print("   ✅ User + expires index for user token queries")
        
        # ==========================================
        # USER PREFERENCES OPTIMIZATION
        # ==========================================
        print("\n📋 Optimizing user preferences...")
        
        # Index on user_id (already unique, but explicit for clarity)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id 
            ON user_preferences(user_id)
        """)
        print("   ✅ User_id index for preference lookups")
        
        # ==========================================
        # DEFAULT CATEGORIES OPTIMIZATION
        # ==========================================
        print("\n📋 Optimizing default categories...")
        
        # Index on name for fast category lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_default_categories_name 
            ON default_categories(name)
        """)
        print("   ✅ Name index for category lookups")
        
        # ==========================================
        # CUSTOM CATEGORIES OPTIMIZATION
        # ==========================================
        print("\n📋 Optimizing custom categories...")
        
        # Composite index for user's custom categories
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_custom_categories_user_id 
            ON custom_categories(user_id)
        """)
        print("   ✅ User_id index for user's custom categories")
        
        # Composite index for name lookups per user
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_custom_categories_user_name 
            ON custom_categories(user_id, name)
        """)
        print("   ✅ User + name index for category validation")
        
        # ==========================================
        # USER CATEGORY BUDGETS OPTIMIZATION
        # ==========================================
        print("\n📋 Optimizing user category budgets...")
        
        # Composite index for user's category budgets
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_category_budgets_user 
            ON user_category_budgets(user_id)
        """)
        print("   ✅ User_id index for budget lookups")
        
        # Composite index for category-specific budgets
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_category_budgets_category 
            ON user_category_budgets(category_id, category_type)
        """)
        print("   ✅ Category + type index for budget queries")
        
        # Composite index for user's category budgets with type
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_category_budgets_user_category 
            ON user_category_budgets(user_id, category_id, category_type)
        """)
        print("   ✅ User + category + type index for budget calculations")
        
        # ==========================================
        # LEGACY CATEGORIES TABLE (if exists)
        # ==========================================
        print("\n📋 Checking legacy categories table...")
        
        # Check if old categories table still exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'categories'
        """)
        
        if cursor.fetchone():
            print("   ⚠️  Legacy categories table found - adding indexes...")
            
            # Index on user_id for legacy categories
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_categories_user_id 
                ON categories(user_id)
            """)
            print("   ✅ User_id index for legacy categories")
            
            # Index on is_default for default category queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_categories_is_default 
                ON categories(is_default)
            """)
            print("   ✅ Is_default index for legacy categories")
        else:
            print("   ✅ Legacy categories table not found (already migrated)")
        
        # Commit all changes
        conn.commit()
        
        print("\n" + "=" * 60)
        print("🎉 Database optimization completed successfully!")
        print("📊 Performance improvements added:")
        print("   • Faster user authentication")
        print("   • Faster expense queries by user and date")
        print("   • Faster category lookups")
        print("   • Better budget tracking performance")
        print("   • Optimized password reset operations")
        print("\n✅ All existing functionality preserved!")
        
        return True
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\n❌ Database optimization failed: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

def analyze_current_performance():
    """Analyze current database performance"""
    print("\n🔍 Analyzing current database performance...")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check table sizes
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                attname,
                n_distinct,
                correlation
            FROM pg_stats 
            WHERE schemaname = 'public' 
            AND tablename IN ('users', 'expenses', 'password_reset_tokens', 'user_preferences')
            ORDER BY tablename, attname
        """)
        
        stats = cursor.fetchall()
        if stats:
            print("📊 Current table statistics:")
            for stat in stats:
                print(f"   {stat[1]}.{stat[2]}: {stat[3]} distinct values")
        
        # Check existing indexes
        cursor.execute("""
            SELECT 
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """)
        
        indexes = cursor.fetchall()
        if indexes:
            print(f"\n📋 Found {len(indexes)} existing indexes:")
            for idx in indexes:
                print(f"   {idx[0]}: {idx[1]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Performance analysis failed: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🌱 Sprout Budget Tracker - Database Optimization")
    print("=" * 60)
    
    # First analyze current state
    analyze_current_performance()
    
    # Run optimization
    success = run_optimization()
    
    if success:
        print("\n✅ Database optimization completed successfully!")
        print("🚀 Your app will now have better performance!")
        exit(0)
    else:
        print("\n❌ Database optimization failed!")
        exit(1)
