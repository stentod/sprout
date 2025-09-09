from flask import Blueprint, request, jsonify
from datetime import datetime, date

from utils import (
    logger, run_query, get_user_daily_limit, _cache, _cache_timestamps
)
from auth import require_auth, get_current_user_id

# Create Blueprint for preferences routes
preferences_bp = Blueprint('preferences', __name__)

@preferences_bp.route('/preferences/daily-limit', methods=['GET'])
@require_auth
def get_daily_limit():
    """Get the user's current daily spending limit"""
    try:
        user_id = get_current_user_id()
        daily_limit = get_user_daily_limit(user_id)
        return jsonify({
            'daily_limit': daily_limit,
            'success': True
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@preferences_bp.route('/preferences/daily-limit', methods=['POST', 'PUT'])
@require_auth
def set_daily_limit():
    """Set the user's daily spending limit"""
    try:
        data = request.get_json()
        daily_limit = data.get('daily_limit')
        
        if daily_limit is None:
            return jsonify({
                'error': 'daily_limit is required',
                'success': False
            }), 400
        
        try:
            daily_limit = float(daily_limit)
            if daily_limit < 0:
                return jsonify({
                    'error': 'daily_limit must be positive',
                    'success': False
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'error': 'daily_limit must be a valid number',
                'success': False
            }), 400
        
        user_id = get_current_user_id()
        
        # Update or insert user preference
        sql = '''
            INSERT INTO user_preferences (user_id, daily_spending_limit, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                daily_spending_limit = EXCLUDED.daily_spending_limit,
                updated_at = CURRENT_TIMESTAMP
            RETURNING daily_spending_limit
        '''
        result = run_query(sql, (user_id, daily_limit), fetch_one=True)
        
        if result:
            # Clear cache for this user's daily limit
            cache_key = f"daily_limit_{user_id}"
            if cache_key in _cache:
                del _cache[cache_key]
            if cache_key in _cache_timestamps:
                del _cache_timestamps[cache_key]
            
            return jsonify({
                'daily_limit': float(result['daily_spending_limit']),
                'success': True,
                'message': 'Daily spending limit updated successfully'
            })
        else:
            return jsonify({
                'error': 'Failed to update daily spending limit',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@preferences_bp.route('/preferences/category-requirement', methods=['GET'])
@require_auth
def get_category_requirement():
    """Get the user's preference for requiring categories"""
    try:
        user_id = get_current_user_id()
        
        sql = 'SELECT require_categories FROM user_preferences WHERE user_id = %s'
        result = run_query(sql, (user_id,), fetch_one=True)
        
        if result:
            require_categories = result['require_categories']
        else:
            # Create default preference if none exists
            sql = '''
                INSERT INTO user_preferences (user_id, require_categories)
                VALUES (%s, TRUE)
                RETURNING require_categories
            '''
            result = run_query(sql, (user_id,), fetch_one=True)
            require_categories = result['require_categories']
        
        return jsonify({
            'require_categories': require_categories,
            'success': True
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@preferences_bp.route('/preferences/category-requirement', methods=['POST', 'PUT'])
@require_auth
def set_category_requirement():
    """Set the user's preference for requiring categories"""
    try:
        data = request.get_json()
        require_categories = data.get('require_categories')
        
        if require_categories is None:
            return jsonify({
                'error': 'require_categories is required',
                'success': False
            }), 400
        
        if not isinstance(require_categories, bool):
            return jsonify({
                'error': 'require_categories must be a boolean',
                'success': False
            }), 400
        
        user_id = get_current_user_id()
        
        # Update or insert user preference
        sql = '''
            INSERT INTO user_preferences (user_id, require_categories, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                require_categories = EXCLUDED.require_categories,
                updated_at = CURRENT_TIMESTAMP
            RETURNING require_categories
        '''
        result = run_query(sql, (user_id, require_categories), fetch_one=True)
        
        if result:
            return jsonify({
                'require_categories': result['require_categories'],
                'success': True,
                'message': f"Category requirement {'enabled' if result['require_categories'] else 'disabled'} successfully"
            })
        else:
            return jsonify({
                'error': 'Failed to update category requirement preference',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@preferences_bp.route('/preferences/budgets', methods=['GET'])
@require_auth
def get_budgets():
    """Get weekly, monthly, and yearly budgets based on daily limit with spending data"""
    try:
        user_id = get_current_user_id()
        daily_limit = get_user_daily_limit(user_id)
        
        
        # Calculate budget periods
        weekly_budget = daily_limit * 7
        monthly_budget = daily_limit * 30  # Using 30 days for consistency
        yearly_budget = daily_limit * 365
        
        # Get spending data for different periods
        # Weekly spending (last 7 days)
        weekly_sql = '''
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses 
            WHERE user_id = %s 
            AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
            AND timestamp < CURRENT_DATE + INTERVAL '1 day'
        '''
        weekly_result = run_query(weekly_sql, (user_id,), fetch_one=True)
        weekly_spent = float(weekly_result['spent']) if weekly_result else 0.0
        
        # Monthly spending (last 30 days)
        monthly_sql = '''
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses 
            WHERE user_id = %s 
            AND timestamp >= CURRENT_DATE - INTERVAL '30 days'
            AND timestamp < CURRENT_DATE + INTERVAL '1 day'
        '''
        monthly_result = run_query(monthly_sql, (user_id,), fetch_one=True)
        monthly_spent = float(monthly_result['spent']) if monthly_result else 0.0
        
        # Yearly spending (last 365 days)
        yearly_sql = '''
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses 
            WHERE user_id = %s 
            AND timestamp >= CURRENT_DATE - INTERVAL '365 days'
            AND timestamp < CURRENT_DATE + INTERVAL '1 day'
        '''
        yearly_result = run_query(yearly_sql, (user_id,), fetch_one=True)
        yearly_spent = float(yearly_result['spent']) if yearly_result else 0.0
        
        return jsonify({
            'success': True,
            'daily_limit': daily_limit,
            'adjusted_daily_limit': daily_limit,
            'budgets': {
                'weekly': {
                    'budget': weekly_budget,
                    'spent': weekly_spent,
                    'remaining': weekly_budget - weekly_spent,
                    'percentage_used': (weekly_spent / weekly_budget * 100) if weekly_budget > 0 else 0
                },
                'monthly': {
                    'budget': monthly_budget,
                    'spent': monthly_spent,
                    'remaining': monthly_budget - monthly_spent,
                    'percentage_used': (monthly_spent / monthly_budget * 100) if monthly_budget > 0 else 0
                },
                'yearly': {
                    'budget': yearly_budget,
                    'spent': yearly_spent,
                    'remaining': yearly_budget - yearly_spent,
                    'percentage_used': (yearly_spent / yearly_budget * 100) if yearly_budget > 0 else 0
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting budgets: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500




# ==========================================
# DATE SIMULATION ENDPOINTS
# ==========================================

@preferences_bp.route('/preferences/date-simulation', methods=['GET'])
@require_auth
def get_date_simulation():
    """Get the current date simulation status"""
    try:
        user_id = get_current_user_id()
        
        # Check if user has a simulated date set
        result = run_query("""
            SELECT simulated_date 
            FROM user_preferences 
            WHERE user_id = %s AND simulated_date IS NOT NULL
        """, (user_id,))
        
        if result and len(result) > 0:
            simulated_date = result[0]['simulated_date']
            return jsonify({
                'success': True,
                'is_simulated': True,
                'simulated_date': simulated_date.strftime('%Y-%m-%d') if simulated_date else None
            })
        else:
            return jsonify({
                'success': True,
                'is_simulated': False,
                'simulated_date': None
            })
            
    except Exception as e:
        logger.error(f"Error getting date simulation: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@preferences_bp.route('/preferences/date-simulation', methods=['POST'])
@require_auth
def set_date_simulation():
    """Set a simulated date for testing"""
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        simulated_date_str = data.get('simulated_date')
        
        if not simulated_date_str:
            return jsonify({
                'error': 'simulated_date is required',
                'success': False
            }), 400
        
        try:
            # Parse and validate the date
            simulated_date = datetime.strptime(simulated_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': 'Invalid date format. Use YYYY-MM-DD',
                'success': False
            }), 400
        
        # Get the previous simulated date BEFORE updating the database
        prev_result = run_query("""
            SELECT simulated_date 
            FROM user_preferences 
            WHERE user_id = %s AND simulated_date IS NOT NULL
        """, (user_id,), fetch_one=True)
        
        # Determine the date to process rollover for
        date_to_process = None
        if prev_result and prev_result['simulated_date']:
            # If there was a previous simulated date, use that
            date_to_process = prev_result['simulated_date']
        else:
            # If no previous simulated date, use today (real date)
            from datetime import date
            date_to_process = date.today()
        
        # Process rollover when changing dates (BEFORE updating the database)
        try:
            from rollover_service import RolloverService
            rollover_service = RolloverService()
            
            # Always process rollover when changing dates
            if date_to_process != simulated_date:
                logger.info(f"🔄 Processing rollover for date transition: {date_to_process} -> {simulated_date}")
                rollover_service.process_end_of_day_rollover(user_id, date_to_process)
                logger.info(f"✅ Processed rollover for date transition: {date_to_process} -> {simulated_date}")
            else:
                logger.info(f"📅 No date change detected, skipping rollover processing")
                
        except Exception as e:
            logger.warning(f"❌ Could not process rollover for date transition: {e}")
            import traceback
            traceback.print_exc()
        
        # Update or insert the simulated date (AFTER processing rollover)
        run_query("""
            INSERT INTO user_preferences (user_id, simulated_date, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (user_id) 
            DO UPDATE SET 
                simulated_date = EXCLUDED.simulated_date,
                updated_at = NOW()
        """, (user_id, simulated_date))
        
        logger.info(f"User {user_id} set simulated date to {simulated_date}")
        
        return jsonify({
            'success': True,
            'message': f'Date simulation set to {simulated_date}',
            'simulated_date': simulated_date_str
        })
        
    except Exception as e:
        logger.error(f"Error setting date simulation: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@preferences_bp.route('/preferences/date-simulation', methods=['DELETE'])
@require_auth
def clear_date_simulation():
    """Clear the simulated date and return to real date"""
    try:
        user_id = get_current_user_id()
        
        # Process rollover before clearing simulated date
        try:
            from rollover_service import RolloverService
            rollover_service = RolloverService()
            
            # Get current simulated date to process rollover
            current_result = run_query("""
                SELECT simulated_date 
                FROM user_preferences 
                WHERE user_id = %s AND simulated_date IS NOT NULL
            """, (user_id,), fetch_one=True)
            
            if current_result and current_result['simulated_date']:
                # Process rollover for the current simulated date before clearing
                rollover_service.process_end_of_day_rollover(user_id, current_result['simulated_date'])
                logger.info(f"Processed rollover before clearing simulated date: {current_result['simulated_date']}")
                
        except Exception as e:
            logger.warning(f"Could not process rollover before clearing date: {e}")
        
        # Clear the simulated date
        run_query("""
            UPDATE user_preferences 
            SET simulated_date = NULL, updated_at = NOW()
            WHERE user_id = %s
        """, (user_id,))
        
        logger.info(f"User {user_id} cleared simulated date")
        
        return jsonify({
            'success': True,
            'message': 'Date simulation cleared, using real date'
        })
        
    except Exception as e:
        logger.error(f"Error clearing date simulation: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500
