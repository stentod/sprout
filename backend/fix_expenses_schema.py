#!/usr/bin/env python3
"""
Database migration script to fix expenses table schema
Adds missing category_id column to expenses table
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    database_url = os.getenv('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')
    return psycopg2.connect(database_url)

def fix_expenses_schema():
    """Add missing category_id column to expenses table"""
    print("🔄 Starting expenses table schema fix...")
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Check if category_id column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'expenses' AND column_name = 'category_id'
        """)
        
        column_exists = cursor.fetchone()
        
        if not column_exists:
            print("➕ Adding category_id column to expenses table...")
            
            # Add the category_id column
            cursor.execute("""
                ALTER TABLE expenses 
                ADD COLUMN category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL
            """)
            
            print("✅ category_id column added successfully")
            
            # Update existing expenses to use a default category (if any exist)
            cursor.execute("SELECT COUNT(*) as count FROM expenses")
            expense_count = cursor.fetchone()
            
            if expense_count and expense_count['count'] > 0:
                print(f"🔄 Found {expense_count['count']} existing expenses, updating them...")
                
                # Get the first available category for user 0 (default user)
                cursor.execute("""
                    SELECT id FROM categories 
                    WHERE user_id = 0 
                    ORDER BY id 
                    LIMIT 1
                """)
                default_category = cursor.fetchone()
                
                if default_category:
                    cursor.execute("""
                        UPDATE expenses 
                        SET category_id = %s 
                        WHERE category_id IS NULL
                    """, (default_category['id'],))
                    print(f"✅ Updated existing expenses to use category {default_category['id']}")
                else:
                    print("⚠️ No default category found, existing expenses will have NULL category_id")
            else:
                print("ℹ️ No existing expenses found")
        else:
            print("ℹ️ category_id column already exists")
        
        # Commit all changes
        conn.commit()
        print("🎉 Expenses table schema fix completed successfully!")
        
        # Show final table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'expenses' 
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print(f"\n📋 Expenses table columns ({len(columns)}):")
        for col in columns:
            print(f"  {col['column_name']} ({col['data_type']}, nullable: {col['is_nullable']})")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    fix_expenses_schema()
