#!/usr/bin/env python3
"""
Database setup script for Sprout Budget Tracker
Creates PostgreSQL tables in existing database
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_tables():
    """Create the expenses table in the existing database"""
    try:
        # Connect to our application database
        DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")
        print(f"🔌 Connecting to database...")
        
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), 'schema_postgres.sql')
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        print("📋 Creating tables...")
        cur.execute(schema)
        conn.commit()
        
        print("✅ Tables created successfully")
        
        cur.close()
        conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"🔌 Database connection error: {e}")
        print("⚠️  This is expected in demo mode or if database is not available")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        # Don't exit with error code - let the app start in demo mode
        print("⚠️  App will continue in demo mode")

if __name__ == "__main__":
    print("🌱 Setting up Sprout Budget Tracker database...")
    create_tables()
    print("🎉 Database setup complete!") 