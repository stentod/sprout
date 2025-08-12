#!/usr/bin/env python3
"""
Database migration script to add email support and password reset functionality.
Run this to upgrade existing databases to support the new authentication features.
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

def migrate_database():
    """Apply migration to add email support"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        print("🔄 Starting database migration for email support...")
        
        # Check if email column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'email'
        """)
        
        email_exists = cursor.fetchone()
        
        if not email_exists:
            print("➕ Adding email column to users table...")
            cursor.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
            
            # Set default email values for existing users
            cursor.execute("""
                UPDATE users 
                SET email = username || '@example.com' 
                WHERE email IS NULL
            """)
            
            # Make email required and unique
            cursor.execute("ALTER TABLE users ALTER COLUMN email SET NOT NULL")
            cursor.execute("ALTER TABLE users ADD CONSTRAINT users_email_unique UNIQUE (email)")
            
            print("✅ Email column added successfully")
        else:
            print("ℹ️  Email column already exists")
        
        # Check if password_reset_tokens table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'password_reset_tokens'
        """)
        
        reset_table_exists = cursor.fetchone()
        
        if not reset_table_exists:
            print("➕ Creating password_reset_tokens table...")
            cursor.execute("""
                CREATE TABLE password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token)")
            cursor.execute("CREATE INDEX idx_password_reset_tokens_expires ON password_reset_tokens(expires_at)")
            
            print("✅ Password reset tokens table created successfully")
        else:
            print("ℹ️  Password reset tokens table already exists")
        
        # Update default user with email if needed
        cursor.execute("SELECT email FROM users WHERE id = 0")
        default_user = cursor.fetchone()
        
        if default_user and '@' not in default_user.get('email', ''):
            cursor.execute("""
                UPDATE users 
                SET email = 'default@example.com' 
                WHERE id = 0
            """)
            print("✅ Updated default user email")
        else:
            print("ℹ️  Default user email already set correctly")
        
        # Commit all changes
        conn.commit()
        print("\n🎉 Database migration completed successfully!")
        
        # Show final user count
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()
        print(f"📊 Total users in database: {user_count['count']}")
        
        print("\n📋 Next steps:")
        print("1. Install Flask-Mail: pip install Flask-Mail")
        print("2. Configure email settings in .env file (copy from env_template.txt)")
        print("3. Restart your application server")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate_database()
