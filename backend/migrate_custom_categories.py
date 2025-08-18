#!/usr/bin/env python3
"""
Migration script to restructure categories into normalized design.
This separates default categories (shared by all users) from custom categories (user-specific).
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def run_migration():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔧 Starting migration: Restructure categories for custom categories support")
        
        # Check if new tables already exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name IN ('default_categories', 'custom_categories', 'user_category_budgets')
        """)
        existing_tables = [row['table_name'] for row in cursor.fetchall()]
        
        if len(existing_tables) == 3:
            print("✅ All new tables already exist, skipping migration")
            return
        
        print("📋 Creating new normalized category tables...")
        
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
        
        # Create user_category_budgets table for budget tracking
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
        
        # Insert default categories
        print("📝 Inserting default categories...")
        default_categories = [
            ('Food & Dining', '🍽️', '#FF6B6B'),
            ('Transportation', '🚗', '#4ECDC4'),
            ('Entertainment', '🎬', '#45B7D1'),
            ('Shopping', '🛍️', '#96CEB4'),
            ('Bills & Utilities', '💡', '#FFEAA7'),
            ('Healthcare', '🏥', '#DDA0DD'),
            ('Education', '📚', '#98D8C8'),
            ('Travel', '✈️', '#F7DC6F'),
            ('Gifts', '🎁', '#BB8FCE'),
            ('Other', '📦', '#A9A9A9')
        ]
        
        for name, icon, color in default_categories:
            cursor.execute("""
                INSERT INTO default_categories (name, icon, color)
                VALUES (%s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """, (name, icon, color))
        
        # Migrate existing custom categories from the old categories table
        print("🔄 Migrating existing custom categories...")
        cursor.execute("""
            SELECT id, user_id, name, icon, color, daily_budget, created_at
            FROM categories 
            WHERE user_id IS NOT NULL AND user_id != 0
        """)
        
        existing_custom_categories = cursor.fetchall()
        migrated_count = 0
        
        for cat in existing_custom_categories:
            try:
                # Insert into custom_categories
                cursor.execute("""
                    INSERT INTO custom_categories (user_id, name, icon, color, daily_budget, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, name) DO NOTHING
                """, (cat['user_id'], cat['name'], cat['icon'], cat['color'], cat['daily_budget'], cat['created_at']))
                
                # Get the new custom category ID
                cursor.execute("""
                    SELECT id FROM custom_categories 
                    WHERE user_id = %s AND name = %s
                """, (cat['user_id'], cat['name']))
                
                new_cat_id = cursor.fetchone()
                if new_cat_id:
                    # Insert budget into user_category_budgets
                    cursor.execute("""
                        INSERT INTO user_category_budgets (user_id, category_id, category_type, daily_budget, created_at)
                        VALUES (%s, %s, 'custom', %s, %s)
                        ON CONFLICT (user_id, category_id, category_type) DO NOTHING
                    """, (cat['user_id'], new_cat_id['id'], cat['daily_budget'], cat['created_at']))
                    
                    migrated_count += 1
                    
            except Exception as e:
                print(f"⚠️ Warning: Could not migrate category '{cat['name']}' for user {cat['user_id']}: {e}")
        
        print(f"✅ Migrated {migrated_count} custom categories")
        
        # Create indexes for better performance
        print("🔍 Creating database indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_custom_categories_user_id ON custom_categories(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_category_budgets_user_id ON user_category_budgets(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_category_budgets_category ON user_category_budgets(category_id, category_type)")
        
        conn.commit()
        print("✅ Successfully restructured categories database")
        print("✅ Default categories are now shared across all users")
        print("✅ Custom categories are user-specific")
        print("✅ Budget tracking is normalized and flexible")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    run_migration()
