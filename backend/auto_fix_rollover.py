"""
Automatic rollover database fix
This script runs on app startup to ensure rollover columns exist
"""

import logging
from utils import run_query

logger = logging.getLogger(__name__)

def fix_rollover_database():
    """Automatically add rollover column if it doesn't exist"""
    try:
        logger.info("Checking rollover database schema...")
        
        # Step 1: Add rollover column if it doesn't exist
        try:
            logger.info("Adding daily_rollover_enabled column...")
            run_query('ALTER TABLE user_preferences ADD COLUMN IF NOT EXISTS daily_rollover_enabled BOOLEAN DEFAULT FALSE', ())
            logger.info("✅ daily_rollover_enabled column ensured")
        except Exception as e:
            logger.warning(f"Column add issue (probably already exists): {e}")
        
        # Step 2: Create rollover table if it doesn't exist
        try:
            logger.info("Creating daily_rollovers table...")
            run_query('''
                CREATE TABLE IF NOT EXISTS daily_rollovers (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    date DATE NOT NULL,
                    rollover_amount DECIMAL(10,2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE(user_id, date)
                )
            ''', ())
            logger.info("✅ daily_rollovers table ensured")
        except Exception as e:
            logger.warning(f"Table create issue (probably already exists): {e}")
        
        # Step 3: Set default values for existing users
        try:
            logger.info("Setting default rollover values...")
            run_query('UPDATE user_preferences SET daily_rollover_enabled = FALSE WHERE daily_rollover_enabled IS NULL', ())
            logger.info("✅ Default rollover values set")
        except Exception as e:
            logger.warning(f"Default values issue: {e}")
        
        logger.info("🎉 Rollover database fix completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Error in rollover database fix: {str(e)}")
        return False

if __name__ == "__main__":
    fix_rollover_database()
