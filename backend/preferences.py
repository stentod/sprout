from flask import Blueprint, request, jsonify

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
        
        # Check if rollover is enabled and get today's rollover amount
        rollover_sql = '''
            SELECT daily_rollover_enabled, 
                   COALESCE((SELECT rollover_amount FROM daily_rollovers WHERE user_id = %s AND date = CURRENT_DATE), 0.00) as today_rollover
            FROM user_preferences 
            WHERE user_id = %s
        '''
        rollover_result = run_query(rollover_sql, (user_id, user_id), fetch_one=True)
        
        daily_rollover_enabled = rollover_result.get('daily_rollover_enabled', False) if rollover_result else False
        today_rollover = float(rollover_result.get('today_rollover', 0.00)) if rollover_result else 0.0
        
        # Calculate adjusted daily limit (including rollover)
        adjusted_daily_limit = daily_limit + today_rollover
        
        # Calculate budget periods
        weekly_budget = adjusted_daily_limit * 7
        monthly_budget = adjusted_daily_limit * 30  # Using 30 days for consistency
        yearly_budget = adjusted_daily_limit * 365
        
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
            'daily_rollover_enabled': daily_rollover_enabled,
            'today_rollover': today_rollover,
            'adjusted_daily_limit': adjusted_daily_limit,
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

@preferences_bp.route('/preferences/rollover-settings', methods=['GET'])
@require_auth
def get_rollover_settings():
    """Get the user's rollover settings"""
    try:
        user_id = get_current_user_id()
        
        # Get rollover setting
        sql = 'SELECT daily_rollover_enabled FROM user_preferences WHERE user_id = %s'
        result = run_query(sql, (user_id,), fetch_one=True)
        
        if result:
            return jsonify({
                'daily_rollover_enabled': result['daily_rollover_enabled'],
                'success': True
            })
        else:
            return jsonify({
                'daily_rollover_enabled': False,
                'success': True
            })
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@preferences_bp.route('/preferences/rollover-settings', methods=['POST', 'PUT'])
@require_auth
def update_rollover_settings():
    """Update the user's rollover settings"""
    try:
        data = request.get_json()
        daily_rollover_enabled = data.get('daily_rollover_enabled', False)
        
        user_id = get_current_user_id()
        
        # Update rollover setting
        sql = '''
            INSERT INTO user_preferences (user_id, daily_rollover_enabled, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id) DO UPDATE SET
                daily_rollover_enabled = EXCLUDED.daily_rollover_enabled,
                updated_at = CURRENT_TIMESTAMP
            RETURNING daily_rollover_enabled
        '''
        result = run_query(sql, (user_id, daily_rollover_enabled), fetch_one=True)
        
        if result:
            return jsonify({
                'daily_rollover_enabled': result['daily_rollover_enabled'],
                'success': True,
                'message': 'Rollover settings updated successfully'
            })
        else:
            return jsonify({
                'error': 'Failed to update rollover settings',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@preferences_bp.route('/preferences/rollover-amounts', methods=['GET'])
@require_auth
def get_rollover_amounts():
    """Get current rollover amounts for daily budget"""
    try:
        user_id = get_current_user_id()
        
        # Get user's rollover setting
        settings_sql = 'SELECT daily_rollover_enabled FROM user_preferences WHERE user_id = %s'
        settings_result = run_query(settings_sql, (user_id,), fetch_one=True)
        
        if not settings_result or not settings_result['daily_rollover_enabled']:
            return jsonify({
                'daily_rollover': 0.0,
                'success': True
            })
        
        # Get today's rollover amount
        daily_sql = '''
            SELECT rollover_amount FROM daily_rollovers 
            WHERE user_id = %s AND date = CURRENT_DATE
        '''
        daily_result = run_query(daily_sql, (user_id,), fetch_one=True)
        daily_rollover = float(daily_result['rollover_amount']) if daily_result else 0.0
        
        return jsonify({
            'daily_rollover': daily_rollover,
            'success': True
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500
