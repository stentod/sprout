#!/usr/bin/env python3
"""
Database setup script for Sprout Budget Tracker
Creates PostgreSQL database and tables
"""

import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to default database to create our database
        conn = psycopg2.connect(
            host=os.environ.get("DB_HOST", "localhost"),
            database=os.environ.get("DB_DEFAULT_NAME", "dstent"),
            user=os.environ.get("DB_USER", "dstent"),
            password=os.environ.get("DB_PASSWORD", "")
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create database
        cur.execute("CREATE DATABASE sprout_budget")
        print("✅ Database 'sprout_budget' created successfully")
        
        cur.close()
        conn.close()
        
    except psycopg2.errors.DuplicateDatabase:
        print("📝 Database 'sprout_budget' already exists")
    except Exception as e:
        print(f"❌ Error creating database: {e}")

def create_tables():
    """Create the expenses table"""
    try:
        # Connect to our application database
        DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Read and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), 'schema_postgres.sql')
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        cur.execute(schema)
        conn.commit()
        
        print("✅ Tables created successfully")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

if __name__ == "__main__":
    print("🌱 Setting up Sprout Budget Tracker database...")
    create_database()
    create_tables()
    print("🎉 Database setup complete!") 