#!/usr/bin/env python3
"""
Script to check and fix production database schema
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_production_database():
    """Check production database schema"""
    print("🔍 Checking Production Database Schema...")
    print("=" * 50)
    
    # Try to get production DATABASE_URL
    DATABASE_URL = os.environ.get("DATABASE_URL")
    
    if not DATABASE_URL:
        print("❌ DATABASE_URL not found in environment")
        print("💡 Make sure you're running this in your production environment")
        return False
    
    try:
        print(f"🔗 Connecting to production database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check users table schema
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print(f"📋 Users table columns ({len(columns)}):")
        
        found_columns = [col[0] for col in columns]
        
        for col in columns:
            print(f"  {col[0]} ({col[1]}, nullable: {col[2]})")
        
        # Check for username column
        if 'username' in found_columns:
            print("\n❌ Username column still exists in production!")
            print("🔧 Production database needs migration to email-only schema")
            
            # Ask if user wants to run migration
            response = input("\nDo you want to run the email-only migration on production? (y/N): ")
            if response.lower() == 'y':
                run_production_migration(cursor, conn)
            else:
                print("⏭️ Skipping migration. Please run it manually later.")
        else:
            print("\n✅ Username column successfully removed from production!")
        
        # Check user count
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Total users in production database: {user_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Production database connection failed: {e}")
        return False

def run_production_migration(cursor, conn):
    """Run email-only migration on production database"""
    print("\n🔄 Running email-only migration on production...")
    
    try:
        # Create backup
        print("📋 Creating backup of users table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_backup_production AS 
            SELECT * FROM users
        """)
        
        # Remove username column
        print("🗑️ Removing username column...")
        cursor.execute("ALTER TABLE users DROP COLUMN IF EXISTS username")
        
        # Update default user
        print("🔄 Updating default user...")
        cursor.execute("""
            UPDATE users 
            SET email = 'default@example.com' 
            WHERE id = 0
        """)
        
        conn.commit()
        print("✅ Production migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Production migration failed: {e}")
        conn.rollback()
        raise

def main():
    """Main function"""
    print("🌱 Sprout Budget Tracker - Production Database Check")
    print("=" * 60)
    
    success = check_production_database()
    
    if success:
        print("\n🎉 Production database check completed!")
        print("\n📋 Next steps:")
        print("1. If migration was needed and completed, test production signup/login")
        print("2. If migration was skipped, run it manually later")
        print("3. Check Render logs for any authentication errors")
    else:
        print("\n❌ Production database check failed!")
        print("Please check your DATABASE_URL and try again.")

if __name__ == "__main__":
    main()
