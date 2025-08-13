#!/usr/bin/env python3
"""
Migration script to remove username requirement and use email-only authentication
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get database connection"""
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")
    return psycopg2.connect(DATABASE_URL)

def migrate_to_email_only():
    """Migrate database to email-only authentication"""
    print("🔄 Starting migration to email-only authentication...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Step 1: Create a backup of existing users
        print("📋 Creating backup of existing users...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users_backup AS 
            SELECT * FROM users
        """)
        
        # Step 2: Check if username column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'username'
        """)
        
        if cursor.fetchone():
            print("🗑️ Removing username column...")
            
            # Step 3: Remove username column
            cursor.execute("ALTER TABLE users DROP COLUMN username")
            print("✅ Username column removed")
        else:
            print("ℹ️ Username column already removed")
        
        # Step 4: Update default user to use email only
        print("🔄 Updating default user...")
        cursor.execute("""
            UPDATE users 
            SET email = 'default@example.com' 
            WHERE id = 0
        """)
        
        # Step 5: Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Step 6: Verify the changes
        cursor.execute("SELECT id, email, created_at FROM users LIMIT 5")
        users = cursor.fetchall()
        print("\n📊 Current users after migration:")
        for user in users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Created: {user[2]}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def update_schema_file():
    """Update the schema file to reflect email-only structure"""
    print("📝 Updating schema file...")
    
    new_schema = """-- PostgreSQL schema for Sprout Budget Tracker (Email-only authentication)

-- Users table for multi-user support with email-only authentication
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Password reset tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  token VARCHAR(255) UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  used BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index for faster token lookups
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires ON password_reset_tokens(expires_at);

-- Categories table for expense categorization
CREATE TABLE IF NOT EXISTS categories (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0,
  name VARCHAR(100) NOT NULL,
  icon VARCHAR(10) DEFAULT '📝',
  color VARCHAR(7) DEFAULT '#6B7280',
  is_default BOOLEAN DEFAULT FALSE,
  daily_budget DECIMAL(10,2) DEFAULT 0.00,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Insert default user if not exists (email-only)
INSERT INTO users (id, email, password_hash) 
VALUES (0, 'default@example.com', 'dummy_hash') 
ON CONFLICT (id) DO NOTHING;

-- Insert default categories for user 0
INSERT INTO categories (name, icon, color, is_default, user_id) VALUES
  ('Food & Dining', '🍽️', '#FF6B6B', TRUE, 0),
  ('Transportation', '🚗', '#4ECDC4', TRUE, 0),
  ('Shopping', '🛒', '#45B7D1', TRUE, 0),
  ('Health & Fitness', '💪', '#96CEB4', TRUE, 0),
  ('Entertainment', '🎬', '#FECA57', TRUE, 0),
  ('Bills & Utilities', '⚡', '#FF9FF3', TRUE, 0),
  ('Other', '📝', '#6B7280', TRUE, 0)
ON CONFLICT DO NOTHING;

-- Expenses table
CREATE TABLE IF NOT EXISTS expenses (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0,
  amount DECIMAL(10,2) NOT NULL,
  description TEXT,
  category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
  timestamp TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- User preferences table for daily spending limits
CREATE TABLE IF NOT EXISTS user_preferences (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL DEFAULT 0 UNIQUE,
  daily_spending_limit DECIMAL(10,2) DEFAULT 30.00,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Insert default preference for user 0
INSERT INTO user_preferences (user_id, daily_spending_limit) 
VALUES (0, 30.00) 
ON CONFLICT (user_id) DO NOTHING;
"""
    
    with open('schema_postgres.sql', 'w') as f:
        f.write(new_schema)
    
    print("✅ Schema file updated")

if __name__ == "__main__":
    print("🌱 Sprout Budget Tracker - Email-Only Authentication Migration")
    print("=" * 60)
    
    try:
        migrate_to_email_only()
        update_schema_file()
        print("\n🎉 Migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Update your app.py to remove username references")
        print("2. Update frontend forms to use email-only")
        print("3. Test the new authentication flow")
        print("4. Deploy to production")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("Please check your database connection and try again.")
