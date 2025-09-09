#!/usr/bin/env python3
"""
Rollover Service - Handles daily budget rollover calculations
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from utils import run_query, logger

class RolloverService:
    """Service for handling daily budget rollover logic"""
    
    def __init__(self):
        self.logger = logger
    
    def is_rollover_enabled(self, user_id):
        """Check if rollover is enabled for a user"""
        try:
            result = run_query("""
                SELECT daily_rollover_enabled 
                FROM user_preferences 
                WHERE user_id = %s
            """, (user_id,), fetch_one=True)
            
            return result['daily_rollover_enabled'] if result else False
            
        except Exception as e:
            self.logger.error(f"Error checking rollover status: {e}")
            return False
    
    def get_user_daily_limit(self, user_id):
        """Get user's base daily spending limit"""
        try:
            result = run_query("""
                SELECT daily_spending_limit 
                FROM user_preferences 
                WHERE user_id = %s
            """, (user_id,), fetch_one=True)
            
            return float(result['daily_spending_limit']) if result else 30.0
            
        except Exception as e:
            self.logger.error(f"Error getting daily limit: {e}")
            return 30.0
    
    def get_amount_spent_on_date(self, user_id, target_date):
        """Get total amount spent by user on a specific date"""
        try:
            result = run_query("""
                SELECT COALESCE(SUM(amount), 0) as total_spent
                FROM expenses 
                WHERE user_id = %s AND DATE(timestamp) = %s
            """, (user_id, target_date), fetch_one=True)
            
            return float(result['total_spent']) if result else 0.0
            
        except Exception as e:
            self.logger.error(f"Error getting amount spent: {e}")
            return 0.0
    
    def calculate_rollover(self, user_id, target_date):
        """Calculate rollover amount for a specific date"""
        try:
            if not self.is_rollover_enabled(user_id):
                self.logger.info(f"Rollover disabled for user {user_id}")
                return 0.0
            
            daily_limit = self.get_user_daily_limit(user_id)
            amount_spent = self.get_amount_spent_on_date(user_id, target_date)
            
            # Get existing rollover for this date (if any)
            existing_rollover = self.get_rollover_for_date(user_id, target_date)
            
            # Total available budget = base daily limit + existing rollover
            total_available = daily_limit + existing_rollover
            
            # Rollover is the unspent amount from the total available budget
            rollover = max(0, total_available - amount_spent)
            
            self.logger.info(f"🔄 Rollover calculation for user {user_id} on {target_date}: "
                           f"base=${daily_limit}, existing_rollover=${existing_rollover}, total_available=${total_available}, spent=${amount_spent}, rollover=${rollover}")
            
            return rollover
            
        except Exception as e:
            self.logger.error(f"Error calculating rollover: {e}")
            return 0.0
    
    def get_rollover_for_date(self, user_id, target_date):
        """Get rollover amount available for a specific date"""
        try:
            result = run_query("""
                SELECT rollover_amount 
                FROM daily_rollovers 
                WHERE user_id = %s AND date = %s
            """, (user_id, target_date), fetch_one=True)
            
            rollover_amount = float(result['rollover_amount']) if result else 0.0
            self.logger.info(f"🔍 Retrieved rollover for user {user_id} on {target_date}: ${rollover_amount}")
            
            return rollover_amount
            
        except Exception as e:
            self.logger.error(f"Error getting rollover for date: {e}")
            return 0.0
    
    def store_rollover(self, user_id, target_date, rollover_amount):
        """Store rollover amount for a specific date"""
        try:
            daily_limit = self.get_user_daily_limit(user_id)
            amount_spent = self.get_amount_spent_on_date(user_id, target_date)
            
            self.logger.info(f"💾 Storing rollover: user {user_id}, date {target_date}, limit ${daily_limit}, spent ${amount_spent}, rollover ${rollover_amount}")
            
            run_query("""
                INSERT INTO daily_rollovers (user_id, date, base_daily_limit, amount_spent, rollover_amount, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, date) 
                DO UPDATE SET 
                    rollover_amount = EXCLUDED.rollover_amount,
                    amount_spent = EXCLUDED.amount_spent,
                    updated_at = NOW()
            """, (user_id, target_date, daily_limit, amount_spent, rollover_amount))
            
            self.logger.info(f"✅ Stored rollover for user {user_id} on {target_date}: ${rollover_amount}")
            
        except Exception as e:
            self.logger.error(f"Error storing rollover: {e}")
    
    def process_end_of_day_rollover(self, user_id, from_date):
        """Process rollover when transitioning from one day to another"""
        try:
            self.logger.info(f"🔄 Processing end-of-day rollover for user {user_id} from {from_date}")
            
            if not self.is_rollover_enabled(user_id):
                self.logger.info(f"Rollover disabled for user {user_id}, skipping")
                return
            
            # Calculate rollover for the day that's ending
            rollover = self.calculate_rollover(user_id, from_date)
            
            # Store rollover for the next day
            next_date = from_date + timedelta(days=1)
            self.store_rollover(user_id, next_date, rollover)
            
            self.logger.info(f"✅ Processed end-of-day rollover: user {user_id}, "
                           f"from {from_date} to {next_date}, rollover: ${rollover}")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing end-of-day rollover: {e}")
    
    def get_effective_daily_budget(self, user_id, target_date):
        """Get the effective daily budget including rollover"""
        try:
            base_budget = self.get_user_daily_limit(user_id)
            
            if not self.is_rollover_enabled(user_id):
                return base_budget
            
            rollover = self.get_rollover_for_date(user_id, target_date)
            effective_budget = base_budget + rollover
            
            self.logger.info(f"Effective budget for user {user_id} on {target_date}: "
                           f"base={base_budget}, rollover={rollover}, total={effective_budget}")
            
            return effective_budget
            
        except Exception as e:
            self.logger.error(f"Error getting effective daily budget: {e}")
            return self.get_user_daily_limit(user_id)
    
    def update_rollover_settings(self, user_id, enabled):
        """Update user's rollover settings"""
        try:
            run_query("""
                INSERT INTO user_preferences (user_id, daily_rollover_enabled, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    daily_rollover_enabled = EXCLUDED.daily_rollover_enabled,
                    updated_at = NOW()
            """, (user_id, enabled))
            
            self.logger.info(f"Updated rollover settings for user {user_id}: enabled={enabled}")
            
        except Exception as e:
            self.logger.error(f"Error updating rollover settings: {e}")
            raise
