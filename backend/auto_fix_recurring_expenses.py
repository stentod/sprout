"""
Automatic recurring expenses database fix
This script runs when the app starts to ensure recurring expenses table exists
"""

import logging
from utils import run_query

logger = logging.getLogger(__name__)

def fix_recurring_expenses_database():
    """Automatically create recurring_expenses table if it doesn't exist"""
    try:
        logger.info("Checking if recurring expenses schema fix is needed...")

        # Create recurring_expenses table if it doesn't exist
        try:
            logger.info("Creating recurring_expenses table...")
            create_recurring_sql = '''
                CREATE TABLE IF NOT EXISTS recurring_expenses (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 0,
                    description TEXT NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    category_id TEXT,
                    frequency VARCHAR(20) NOT NULL CHECK (frequency IN ('daily', 'weekly', 'monthly')),
                    start_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            '''
            run_query(create_recurring_sql, (), fetch_one=False, fetch_all=False)
            logger.info("✅ Created recurring_expenses table")
        except Exception as e:
            logger.error(f"Error creating recurring_expenses table: {e}", exc_info=True)
            return False

        logger.info("🎉 Recurring expenses schema fix completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Unhandled error during recurring expenses schema fix: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    fix_recurring_expenses_database()
