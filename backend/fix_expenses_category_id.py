#!/usr/bin/env python3
"""
Migration script to update expenses table to handle string category IDs.
This changes the category_id column from INTEGER to VARCHAR to support the new format.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

def get_database_url():
    return os.environ.get('DATABASE_URL', 'postgresql://dstent@localhost/sprout_budget')

def fix_expenses_category_id():
    conn = None
    try:
        conn = psycopg2.connect(get_database_url())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        print("🔧 Fixing expenses table category_id column to support string IDs")
        
        # Check current column type
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'expenses' 
            AND column_name = 'category_id'
        """)
        
        result = cursor.fetchone()
        if result:
            current_type = result['data_type']
            print(f"📋 Current category_id type: {current_type}")
            
            if current_type == 'character varying':
                print("✅ category_id column is already VARCHAR, no changes needed")
                return
            elif current_type == 'integer':
                print("🔄 Converting category_id from INTEGER to VARCHAR...")
                
                # First, drop the foreign key constraint
                cursor.execute("""
                    ALTER TABLE expenses 
                    DROP CONSTRAINT IF EXISTS expenses_category_id_fkey
                """)
                print("   ✅ Dropped foreign key constraint")
                
                # Change column type to VARCHAR
                cursor.execute("""
                    ALTER TABLE expenses 
                    ALTER COLUMN category_id TYPE VARCHAR(50)
                """)
                print("   ✅ Changed column type to VARCHAR(50)")
                
                # Update existing category_id values to use the new format
                cursor.execute("""
                    UPDATE expenses 
                    SET category_id = CONCAT('default_', category_id::text)
                    WHERE category_id IS NOT NULL
                """)
                print(f"   ✅ Updated {cursor.rowcount} existing expenses to new format")
                
                conn.commit()
                print("🎉 Successfully updated expenses table for string category IDs")
            else:
                print(f"⚠️ Unexpected column type: {current_type}")
        else:
            print("❌ category_id column not found in expenses table")
            
    except Exception as e:
        if conn: conn.rollback()
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    fix_expenses_category_id()
