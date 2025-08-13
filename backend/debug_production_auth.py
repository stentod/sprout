#!/usr/bin/env python3
"""
Debug script to identify production authentication issues
"""
import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    print("=" * 50)
    
    required_vars = [
        'DATABASE_URL',
        'SECRET_KEY', 
        'FLASK_ENV',
        'MAIL_USERNAME',
        'MAIL_PASSWORD',
        'MAIL_DEFAULT_SENDER',
        'BASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if 'password' in var.lower() or 'secret' in var.lower():
                masked_value = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '***'
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: NOT SET")
            missing_vars.append(var)
    
    print(f"\n📊 Summary: {len(required_vars) - len(missing_vars)}/{len(required_vars)} variables set")
    if missing_vars:
        print(f"❌ Missing: {', '.join(missing_vars)}")
    else:
        print("✅ All required variables are set!")
    
    return len(missing_vars) == 0

def check_database():
    """Check database connection and schema"""
    print("\n🗄️ Checking Database Connection...")
    print("=" * 50)
    
    try:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            print("❌ DATABASE_URL not set")
            return False
        
        print(f"🔗 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if users table exists and has correct schema
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        print(f"📋 Users table columns ({len(columns)}):")
        
        expected_columns = ['id', 'email', 'password_hash', 'created_at']
        found_columns = [col[0] for col in columns]
        
        for col in columns:
            status = "✅" if col[0] in expected_columns else "⚠️"
            print(f"  {status} {col[0]} ({col[1]}, nullable: {col[2]})")
        
        # Check for username column (should not exist)
        if 'username' in found_columns:
            print("❌ Username column still exists - migration may have failed")
            return False
        else:
            print("✅ Username column successfully removed")
        
        # Check user count
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Total users in database: {user_count}")
        
        # Check recent users
        cursor.execute("SELECT id, email, created_at FROM users ORDER BY created_at DESC LIMIT 5")
        recent_users = cursor.fetchall()
        print(f"📅 Recent users:")
        for user in recent_users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Created: {user[2]}")
        
        cursor.close()
        conn.close()
        print("✅ Database connection successful!")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_flask_config():
    """Check Flask configuration"""
    print("\n⚙️ Checking Flask Configuration...")
    print("=" * 50)
    
    try:
        from app import app
        
        print(f"🔧 Flask Environment: {app.config.get('ENV', 'Not set')}")
        print(f"🔧 Debug Mode: {app.debug}")
        print(f"🔧 Secret Key Set: {'Yes' if app.secret_key else 'No'}")
        
        # Check session configuration
        print(f"🍪 Session Cookie Secure: {app.config.get('SESSION_COOKIE_SECURE', 'Not set')}")
        print(f"🍪 Session Cookie HTTPOnly: {app.config.get('SESSION_COOKIE_HTTPONLY', 'Not set')}")
        print(f"🍪 Session Cookie SameSite: {app.config.get('SESSION_COOKIE_SAMESITE', 'Not set')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Flask configuration check failed: {e}")
        return False

def main():
    """Main debug function"""
    print("🐛 Sprout Budget Tracker - Production Debug")
    print("=" * 60)
    
    env_ok = check_environment()
    db_ok = check_database()
    flask_ok = check_flask_config()
    
    print("\n" + "=" * 60)
    print("📋 DEBUG SUMMARY:")
    print(f"  Environment Variables: {'✅' if env_ok else '❌'}")
    print(f"  Database Connection: {'✅' if db_ok else '❌'}")
    print(f"  Flask Configuration: {'✅' if flask_ok else '❌'}")
    
    if env_ok and db_ok and flask_ok:
        print("\n🎉 All checks passed! The issue might be:")
        print("  - Network/firewall issues")
        print("  - Render deployment not updated")
        print("  - Browser cache issues")
        print("  - CORS configuration")
    else:
        print("\n🔧 Issues found! Please fix the problems above.")
        if not env_ok:
            print("  → Set missing environment variables in Render")
        if not db_ok:
            print("  → Check database connection and run migration")
        if not flask_ok:
            print("  → Check Flask configuration")

if __name__ == "__main__":
    main()
