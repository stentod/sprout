#!/usr/bin/env python3
"""
Deployment script that includes database migration
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_deployment_migration():
    """Run migration during deployment"""
    print("🚀 Running deployment migration...")
    
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found")
        return False
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if username column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'username'
        """)
        
        if cursor.fetchone():
            print("🔄 Username column found - running migration...")
            
            # Create backup
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users_backup_deployment AS 
                SELECT * FROM users
            """)
            
            # Remove username column
            cursor.execute("ALTER TABLE users DROP COLUMN username")
            
            # Update default user
            cursor.execute("""
                UPDATE users 
                SET email = 'default@example.com' 
                WHERE id = 0
            """)
            
            conn.commit()
            print("✅ Migration completed successfully!")
        else:
            print("✅ Username column already removed - no migration needed")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🌱 Sprout Budget Tracker - Deployment Migration")
    print("=" * 50)
    
    if run_deployment_migration():
        print("🎉 Deployment migration successful!")
    else:
        print("❌ Deployment migration failed!")
        exit(1)
