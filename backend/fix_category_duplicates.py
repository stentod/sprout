#!/usr/bin/env python3
"""
Fix category duplicates by ensuring only the new normalized structure is used.
This script will clean up any old category data and ensure only 7 default categories exist.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def fix_category_duplicates():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔧 FIXING CATEGORY DUPLICATES")
        
        # Step 1: Ensure new tables exist
        print("\n📋 Step 1: Creating new tables if they don't exist...")
        
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
        
        # Step 2: Completely clear default_categories and recreate
        print("\n🗑️ Step 2: Clearing all default categories...")
        cursor.execute("DELETE FROM default_categories")
        print(f"   Deleted {cursor.rowcount} existing default categories")
        
        # Step 3: Insert exactly 7 original categories
        print("\n📝 Step 3: Inserting exactly 7 original categories...")
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
        
        # Step 4: Migrate any custom categories from old table
        print("\n🔄 Step 4: Migrating custom categories from old table...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'categories'
        """)
        
        if cursor.fetchone():
            # Check for custom categories in old table
            cursor.execute("""
                SELECT id, user_id, name, icon, color, daily_budget, created_at
                FROM categories 
                WHERE user_id IS NOT NULL AND user_id != 0 AND is_default = FALSE
            """)
            
            old_custom_categories = cursor.fetchall()
            migrated_count = 0
            
            for cat in old_custom_categories:
                try:
                    cursor.execute("""
                        INSERT INTO custom_categories (user_id, name, icon, color, daily_budget, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, name) DO NOTHING
                    """, (cat['user_id'], cat['name'], cat['icon'], cat['color'], cat['daily_budget'], cat['created_at']))
                    
                    if cursor.rowcount > 0:
                        migrated_count += 1
                        
                except Exception as e:
                    print(f"   ⚠️ Could not migrate category '{cat['name']}': {e}")
            
            print(f"   Migrated {migrated_count} custom categories")
        
        # Step 5: Verify the result
        print("\n✅ Step 5: Verifying results...")
        cursor.execute("SELECT id, name, icon FROM default_categories ORDER BY name")
        final_categories = cursor.fetchall()
        
        print(f"📋 Final default categories ({len(final_categories)}):")
        for cat in final_categories:
            print(f"   {cat['id']}: {cat['icon']} {cat['name']}")
        
        # Check for duplicates
        names = [cat['name'] for cat in final_categories]
        duplicates = [name for name in set(names) if names.count(name) > 1]
        
        if duplicates:
            print(f"\n⚠️ WARNING: Still have duplicates: {duplicates}")
        else:
            print("\n✅ No duplicates - fix successful!")
        
        conn.commit()
        print("\n🎉 CATEGORY DUPLICATES FIXED!")
        print("   - Exactly 7 default categories")
        print("   - No duplicates")
        print("   - Custom categories preserved")
        
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Fix failed: {e}")
        sys.exit(1)
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    fix_category_duplicates()
