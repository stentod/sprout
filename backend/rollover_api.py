#!/usr/bin/env python3
"""
Rollover API endpoints
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date
from rollover_service import RolloverService
from auth import require_auth, get_current_user_id
from utils import logger

# Create Blueprint for rollover routes
rollover_bp = Blueprint('rollover', __name__)

# Initialize rollover service
rollover_service = RolloverService()

@rollover_bp.route('/rollover/settings', methods=['GET'])
@require_auth
def get_rollover_settings():
    """Get the user's rollover settings"""
    try:
        user_id = get_current_user_id()
        
        enabled = rollover_service.is_rollover_enabled(user_id)
        
        return jsonify({
            'success': True,
            'daily_rollover_enabled': enabled,
            'message': 'Rollover settings retrieved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error getting rollover settings: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@rollover_bp.route('/rollover/settings', methods=['POST'])
@require_auth
def update_rollover_settings():
    """Update the user's rollover settings"""
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        
        if not data:
            return jsonify({
                'error': 'Request body is required',
                'success': False
            }), 400
        
        daily_rollover_enabled = data.get('daily_rollover_enabled', False)
        
        # Update rollover settings
        rollover_service.update_rollover_settings(user_id, daily_rollover_enabled)
        
        return jsonify({
            'success': True,
            'daily_rollover_enabled': daily_rollover_enabled,
            'message': 'Rollover settings updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating rollover settings: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@rollover_bp.route('/rollover/current-budget', methods=['GET'])
@require_auth
def get_current_budget():
    """Get current effective daily budget including rollover"""
    try:
        user_id = get_current_user_id()
        
        # Get current date (or simulated date if set)
        current_date = date.today()
        
        # Check if user has a simulated date set
        from utils import run_query
        result = run_query("""
            SELECT simulated_date 
            FROM user_preferences 
            WHERE user_id = %s AND simulated_date IS NOT NULL
        """, (user_id,), fetch_one=True)
        
        if result and result['simulated_date']:
            current_date = result['simulated_date']
        
        # Get effective budget and subtract expenses
        base_budget = rollover_service.get_user_daily_limit(user_id)
        rollover_amount = rollover_service.get_rollover_for_date(user_id, current_date)
        total_available = rollover_service.get_effective_daily_budget(user_id, current_date)
        
        # Get amount spent on current date
        amount_spent = rollover_service.get_amount_spent_on_date(user_id, current_date)
        
        # Calculate remaining budget (total available - amount spent)
        remaining_budget = max(0, total_available - amount_spent)
        
        return jsonify({
            'success': True,
            'base_daily_limit': base_budget,
            'rollover_amount': rollover_amount,
            'total_available': total_available,
            'amount_spent': amount_spent,
            'effective_budget': remaining_budget,  # This is the remaining budget after expenses
            'date': current_date.strftime('%Y-%m-%d'),
            'rollover_enabled': rollover_service.is_rollover_enabled(user_id)
        })
        
    except Exception as e:
        logger.error(f"Error getting current budget: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@rollover_bp.route('/rollover/process-day-transition', methods=['POST'])
@require_auth
def process_day_transition():
    """Process rollover when transitioning between days (for date simulation)"""
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        
        if not data or 'from_date' not in data:
            return jsonify({
                'error': 'from_date is required',
                'success': False
            }), 400
        
        from_date_str = data['from_date']
        
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'error': 'Invalid date format. Use YYYY-MM-DD',
                'success': False
            }), 400
        
        # Process rollover for the day transition
        rollover_service.process_end_of_day_rollover(user_id, from_date)
        
        return jsonify({
            'success': True,
            'message': f'Rollover processed for transition from {from_date}',
            'from_date': from_date_str
        })
        
    except Exception as e:
        logger.error(f"Error processing day transition: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@rollover_bp.route('/rollover/history', methods=['GET'])
@require_auth
def get_rollover_history():
    """Get rollover history for the user"""
    try:
        user_id = get_current_user_id()
        
        # Get rollover history for the last 30 days
        from utils import run_query
        result = run_query("""
            SELECT date, base_daily_limit, amount_spent, rollover_amount
            FROM daily_rollovers 
            WHERE user_id = %s 
            AND date >= CURRENT_DATE - INTERVAL '30 days'
            ORDER BY date DESC
        """, (user_id,))
        
        history = []
        for row in result:
            history.append({
                'date': row['date'].strftime('%Y-%m-%d'),
                'base_daily_limit': float(row['base_daily_limit']),
                'amount_spent': float(row['amount_spent']),
                'rollover_amount': float(row['rollover_amount'])
            })
        
        return jsonify({
            'success': True,
            'history': history,
            'message': 'Rollover history retrieved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error getting rollover history: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500
