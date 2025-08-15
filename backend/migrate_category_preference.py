#!/usr/bin/env python3
"""
Migration script to add require_categories column to user_preferences table.
This allows users to choose whether categories are required when adding expenses.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    """Get database URL from environment variable"""
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def run_migration():
    """Run the migration to add require_categories column"""
    conn = None
    try:
        # Connect to database
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔧 Starting migration: Add require_categories to user_preferences")
        
        # Check if column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_preferences' 
            AND column_name = 'require_categories'
        """)
        
        if cursor.fetchone():
            print("✅ Column 'require_categories' already exists, skipping migration")
            return
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE user_preferences 
            ADD COLUMN require_categories BOOLEAN DEFAULT TRUE
        """)
        
        # Update existing records to have require_categories = TRUE (default behavior)
        cursor.execute("""
            UPDATE user_preferences 
            SET require_categories = TRUE 
            WHERE require_categories IS NULL
        """)
        
        conn.commit()
        print("✅ Successfully added require_categories column to user_preferences table")
        print("✅ All existing users will have categories required by default")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
