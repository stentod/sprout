"""
Cleanup script for phantom recurring expenses
This script helps identify and clean up duplicate/phantom expenses
"""

import logging
from datetime import datetime, date, timedelta
from utils import run_query, logger

def cleanup_phantom_expenses():
    """Clean up phantom expenses and old recurring expense data"""
    try:
        logger.info("🧹 Starting phantom expenses cleanup...")
        
        # 1. Check for duplicate expenses (same user, amount, description, date)
        logger.info("🔍 Checking for duplicate expenses...")
        duplicate_sql = '''
            SELECT 
                user_id,
                amount,
                description,
                DATE(timestamp) as expense_date,
                category_id,
                COUNT(*) as duplicate_count,
                ARRAY_AGG(id ORDER BY timestamp) as expense_ids
            FROM expenses 
            WHERE DATE(timestamp) >= %s
            GROUP BY user_id, amount, description, DATE(timestamp), category_id
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
        '''
        
        # Check last 7 days for duplicates
        seven_days_ago = date.today() - timedelta(days=7)
        duplicates = run_query(duplicate_sql, (seven_days_ago,), fetch_all=True)
        
        if duplicates:
            logger.info(f"Found {len(duplicates)} sets of duplicate expenses:")
            for dup in duplicates:
                logger.info(f"  - User {dup['user_id']}: {dup['description']} (${dup['amount']}) on {dup['expense_date']} - {dup['duplicate_count']} duplicates")
        else:
            logger.info("✅ No duplicate expenses found")
        
        # 2. Check for old recurring expenses (created more than 30 days ago)
        logger.info("🔍 Checking for old recurring expenses...")
        old_recurring_sql = '''
            SELECT 
                id,
                user_id,
                description,
                amount,
                frequency,
                start_date,
                created_at,
                is_active
            FROM recurring_expenses 
            WHERE created_at < %s
            ORDER BY created_at ASC
        '''
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        old_recurring = run_query(old_recurring_sql, (thirty_days_ago,), fetch_all=True)
        
        if old_recurring:
            logger.info(f"Found {len(old_recurring)} old recurring expenses:")
            for old in old_recurring:
                logger.info(f"  - ID {old['id']}: {old['description']} (${old['amount']}) - Created: {old['created_at']}, Active: {old['is_active']}")
        else:
            logger.info("✅ No old recurring expenses found")
        
        # 3. Check for suspicious expense patterns (many expenses on same day)
        logger.info("🔍 Checking for suspicious expense patterns...")
        suspicious_sql = '''
            SELECT 
                user_id,
                DATE(timestamp) as expense_date,
                COUNT(*) as expense_count,
                SUM(amount) as total_amount
            FROM expenses 
            WHERE DATE(timestamp) >= %s
            GROUP BY user_id, DATE(timestamp)
            HAVING COUNT(*) >= 10
            ORDER BY expense_count DESC
        '''
        
        suspicious = run_query(suspicious_sql, (seven_days_ago,), fetch_all=True)
        
        if suspicious:
            logger.info(f"Found {len(suspicious)} suspicious expense patterns:")
            for sus in suspicious:
                logger.info(f"  - User {sus['user_id']}: {sus['expense_count']} expenses on {sus['expense_date']} (Total: ${sus['total_amount']})")
        else:
            logger.info("✅ No suspicious expense patterns found")
        
        logger.info("🎯 Phantom expenses analysis complete!")
        return {
            'duplicates': len(duplicates) if duplicates else 0,
            'old_recurring': len(old_recurring) if old_recurring else 0,
            'suspicious_patterns': len(suspicious) if suspicious else 0
        }
        
    except Exception as e:
        logger.error(f"Error during phantom expenses cleanup: {e}")
        return None

def deactivate_old_recurring_expenses():
    """Deactivate old recurring expenses to prevent future phantom expenses"""
    try:
        logger.info("🔧 Deactivating old recurring expenses...")
        
        # Deactivate recurring expenses created more than 30 days ago
        deactivate_sql = '''
            UPDATE recurring_expenses 
            SET is_active = FALSE, updated_at = NOW()
            WHERE created_at < %s AND is_active = TRUE
        '''
        
        thirty_days_ago = datetime.now() - timedelta(days=30)
        result = run_query(deactivate_sql, (thirty_days_ago,), fetch_one=False, fetch_all=False)
        
        logger.info("✅ Old recurring expenses deactivated")
        return True
        
    except Exception as e:
        logger.error(f"Error deactivating old recurring expenses: {e}")
        return False

if __name__ == "__main__":
    # Run the cleanup analysis
    results = cleanup_phantom_expenses()
    
    if results:
        print(f"\n📊 Cleanup Results:")
        print(f"  - Duplicate expenses: {results['duplicates']}")
        print(f"  - Old recurring expenses: {results['old_recurring']}")
        print(f"  - Suspicious patterns: {results['suspicious_patterns']}")
        
        # Ask user if they want to deactivate old recurring expenses
        if results['old_recurring'] > 0:
            print(f"\n⚠️ Found {results['old_recurring']} old recurring expenses that could cause phantom expenses.")
            print("Run deactivate_old_recurring_expenses() to deactivate them.")
