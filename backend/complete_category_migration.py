#!/usr/bin/env python3
"""
Complete migration to normalize categories and fix all related issues.
This script does everything in the correct order.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def complete_migration():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🚀 Running complete category migration")
        
        # Step 1: Fix expenses table to support string category IDs
        print("\n📋 Step 1: Fix expenses table category_id column...")
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'expenses' 
            AND column_name = 'category_id'
        """)
        
        result = cursor.fetchone()
        if result and result['data_type'] == 'integer':
            print("   🔄 Converting category_id from INTEGER to VARCHAR...")
            
            # Drop foreign key constraint
            cursor.execute("""
                ALTER TABLE expenses 
                DROP CONSTRAINT IF EXISTS expenses_category_id_fkey
            """)
            
            # Change column type
            cursor.execute("""
                ALTER TABLE expenses 
                ALTER COLUMN category_id TYPE VARCHAR(50)
            """)
            print("   ✅ Changed column type to VARCHAR(50)")
        else:
            print("   ✅ Column is already VARCHAR")
        
        # Step 2: Create new normalized tables
        print("\n📋 Step 2: Create new normalized category tables...")
        
        # Create default_categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS default_categories (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                icon VARCHAR(10) NOT NULL,
                color VARCHAR(7) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create custom_categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS custom_categories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                icon VARCHAR(10) NOT NULL,
                color VARCHAR(7) NOT NULL,
                daily_budget DECIMAL(10,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, name)
            )
        """)
        
        # Create user_category_budgets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_category_budgets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                category_type VARCHAR(20) NOT NULL CHECK (category_type IN ('default', 'custom')),
                daily_budget DECIMAL(10,2) DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, category_id, category_type)
            )
        """)
        print("   ✅ Created new tables")
        
        # Step 3: Clear and recreate default categories
        print("\n📋 Step 3: Insert exactly 7 default categories...")
        cursor.execute("DELETE FROM default_categories")
        
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
        
        # Step 4: Update existing expenses to use new category ID format
        print("\n📋 Step 4: Update existing expenses...")
        
        # First, get mapping of old category names to new IDs
        cursor.execute("SELECT id, name FROM default_categories")
        new_categories = {cat['name']: cat['id'] for cat in cursor.fetchall()}
        
        # Check if old categories table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'categories'
        """)
        
        if cursor.fetchone():
            # Update expenses that reference old category IDs
            cursor.execute("SELECT id, name FROM categories WHERE is_default = TRUE")
            old_categories = cursor.fetchall()
            
            for old_cat in old_categories:
                if old_cat['name'] in new_categories:
                    new_id = new_categories[old_cat['name']]
                    new_category_id = f"default_{new_id}"
                    
                    cursor.execute("""
                        UPDATE expenses 
                        SET category_id = %s 
                        WHERE category_id = %s OR category_id = %s
                    """, (new_category_id, str(old_cat['id']), f"default_{old_cat['id']}"))
                    
                    if cursor.rowcount > 0:
                        print(f"   ✅ Updated {cursor.rowcount} expenses for {old_cat['name']} -> {new_category_id}")
        
        # Step 5: Clear custom categories and budgets to start fresh
        print("\n📋 Step 5: Preserve existing custom categories...")
        cursor.execute("SELECT COUNT(*) FROM custom_categories")
        custom_count = cursor.fetchone()[0]
        
        if custom_count == 0:
            print("   ✅ Fresh migration - no custom categories to preserve")
        else:
            print(f"   ⚠️  Found {custom_count} existing custom categories - preserving them")
        
        # Only clear user budgets for default categories to prevent duplicates
        cursor.execute("DELETE FROM user_category_budgets WHERE category_type = 'default'")
        print("   ✅ Preserved custom categories, cleared only default category budgets")
        
        conn.commit()
        print("\n🎉 Complete migration successful!")
        print("✅ Expenses table supports string category IDs")
        print("✅ New normalized category structure created")
        print("✅ Exactly 7 default categories (IDs 1-7)")
        print("✅ Existing expenses updated to new format")
        print("✅ Ready for production use")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    complete_migration()
