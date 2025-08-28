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
