"""
Recurring Expenses Module
Handles recurring expense creation, management, and automatic processing
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date, timedelta
import logging

from utils import run_query, logger
from auth import require_auth, get_current_user_id

recurring_expenses_bp = Blueprint('recurring_expenses', __name__)

@recurring_expenses_bp.route('/recurring-expenses', methods=['GET'])
@require_auth
def get_recurring_expenses():
    """Get all recurring expenses for the current user"""
    try:
        user_id = get_current_user_id()
        
        sql = '''
            SELECT 
                re.id,
                re.description,
                re.amount,
                re.category_id,
                re.frequency,
                re.start_date,
                re.is_active,
                re.created_at
            FROM recurring_expenses re
            WHERE re.user_id = %s
            ORDER BY re.created_at DESC
        '''
        
        results = run_query(sql, (user_id,), fetch_all=True)
        
        recurring_expenses = []
        for row in results:
            expense_data = {
                'id': row['id'],
                'description': row['description'],
                'amount': float(row['amount']),
                'frequency': row['frequency'],
                'start_date': row['start_date'].isoformat() if row['start_date'] else None,
                'is_active': row['is_active'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            }
            
            # Get category info if category_id exists
            if row['category_id']:
                try:
                    # Parse category ID to determine type and get details
                    if isinstance(row['category_id'], str) and '_' in row['category_id']:
                        category_type, cat_id = row['category_id'].split('_', 1)
                        numeric_id = int(cat_id)
                    else:
                        numeric_id = int(row['category_id'])
                        category_type = 'custom'
                    
                    # Get category details
                    if category_type == 'default':
                        cat_sql = 'SELECT name, icon, color FROM default_categories WHERE id = %s'
                        cat_result = run_query(cat_sql, (numeric_id,), fetch_one=True)
                        is_default = True
                    else:
                        cat_sql = 'SELECT name, icon, color FROM custom_categories WHERE id = %s AND user_id = %s'
                        cat_result = run_query(cat_sql, (numeric_id, user_id), fetch_one=True)
                        is_default = False
                    
                    if cat_result:
                        expense_data['category'] = {
                            'id': row['category_id'],
                            'name': cat_result['name'],
                            'icon': cat_result['icon'],
                            'color': cat_result['color'],
                            'is_default': is_default
                        }
                except (ValueError, TypeError):
                    # If parsing fails, just skip the category
                    pass
            
            recurring_expenses.append(expense_data)
        
        return jsonify({
            'success': True,
            'recurring_expenses': recurring_expenses
        })
        
    except Exception as e:
        logger.error(f"Error getting recurring expenses: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@recurring_expenses_bp.route('/recurring-expenses', methods=['POST'])
@require_auth
def create_recurring_expense():
    """Create a new recurring expense"""
    try:
        data = request.get_json()
        user_id = get_current_user_id()
        
        # Validate required fields
        required_fields = ['description', 'amount', 'frequency', 'start_date']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    'error': f'Missing required field: {field}',
                    'success': False
                }), 400
        
        description = data['description'].strip()
        amount = float(data['amount'])
        frequency = data['frequency'].lower()
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        category_id = data.get('category_id')
        
        # Validate frequency
        if frequency not in ['daily', 'weekly', 'monthly']:
            return jsonify({
                'error': 'Frequency must be daily, weekly, or monthly',
                'success': False
            }), 400
        
        # Validate amount
        if amount <= 0:
            return jsonify({
                'error': 'Amount must be greater than 0',
                'success': False
            }), 400
        
        # Validate category if provided
        if category_id:
            # Parse category ID to check if it's default or custom
            if isinstance(category_id, str) and '_' in category_id:
                category_type, cat_id = category_id.split('_', 1)
                numeric_id = int(cat_id)
            else:
                numeric_id = int(category_id)
                category_type = 'custom'
            
            # Check if category exists
            if category_type == 'default':
                category_sql = 'SELECT id FROM default_categories WHERE id = %s'
                category_result = run_query(category_sql, (numeric_id,), fetch_one=True)
            else:
                category_sql = 'SELECT id FROM custom_categories WHERE id = %s AND user_id = %s'
                category_result = run_query(category_sql, (numeric_id, user_id), fetch_one=True)
            
            if not category_result:
                return jsonify({
                    'error': 'Invalid category',
                    'success': False
                }), 400
        
        # Insert recurring expense
        insert_sql = '''
            INSERT INTO recurring_expenses (user_id, description, amount, category_id, frequency, start_date)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, created_at
        '''
        
        result = run_query(insert_sql, (user_id, description, amount, category_id, frequency, start_date), fetch_one=True)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Recurring expense created successfully',
                'recurring_expense': {
                    'id': result['id'],
                    'created_at': result['created_at'].isoformat()
                }
            })
        else:
            return jsonify({
                'error': 'Failed to create recurring expense',
                'success': False
            }), 500
            
    except ValueError as e:
        return jsonify({
            'error': 'Invalid date or amount format',
            'success': False
        }), 400
    except Exception as e:
        logger.error(f"Error creating recurring expense: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@recurring_expenses_bp.route('/recurring-expenses/<int:expense_id>', methods=['DELETE'])
@require_auth
def delete_recurring_expense(expense_id):
    """Delete a recurring expense"""
    try:
        user_id = get_current_user_id()
        
        # Check if expense exists and belongs to user
        check_sql = 'SELECT id FROM recurring_expenses WHERE id = %s AND user_id = %s'
        check_result = run_query(check_sql, (expense_id, user_id), fetch_one=True)
        
        if not check_result:
            return jsonify({
                'error': 'Recurring expense not found',
                'success': False
            }), 404
        
        # Delete the expense
        delete_sql = 'DELETE FROM recurring_expenses WHERE id = %s AND user_id = %s'
        run_query(delete_sql, (expense_id, user_id))
        
        return jsonify({
            'success': True,
            'message': 'Recurring expense deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting recurring expense: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

def process_recurring_expenses():
    """Process recurring expenses and add them to the expenses table if due"""
    try:
        logger.info("Processing recurring expenses...")
        today = date.today()
        
        # Get all active recurring expenses
        sql = '''
            SELECT 
                re.id,
                re.user_id,
                re.description,
                re.amount,
                re.category_id,
                re.frequency,
                re.start_date
            FROM recurring_expenses re
            WHERE re.is_active = TRUE
        '''
        
        recurring_expenses = run_query(sql, (), fetch_all=True)
        
        processed_count = 0
        
        for expense in recurring_expenses:
            if is_recurring_expense_due(expense, today):
                # Check if expense already exists for today
                existing_sql = '''
                    SELECT id FROM expenses 
                    WHERE user_id = %s 
                    AND description = %s 
                    AND amount = %s 
                    AND DATE(timestamp) = %s
                '''
                existing = run_query(existing_sql, (
                    expense['user_id'],
                    expense['description'],
                    expense['amount'],
                    today
                ), fetch_one=True)
                
                if not existing:
                    # Add the expense
                    insert_sql = '''
                        INSERT INTO expenses (user_id, amount, description, category_id, timestamp)
                        VALUES (%s, %s, %s, %s, %s)
                    '''
                    run_query(insert_sql, (
                        expense['user_id'],
                        expense['amount'],
                        expense['description'],
                        expense['category_id'],
                        datetime.now()
                    ))
                    processed_count += 1
                    logger.info(f"Added recurring expense: {expense['description']} for user {expense['user_id']}")
        
        logger.info(f"Processed {processed_count} recurring expenses")
        return processed_count
        
    except Exception as e:
        logger.error(f"Error processing recurring expenses: {e}")
        return 0

def is_recurring_expense_due(expense, check_date):
    """Check if a recurring expense is due on the given date"""
    start_date = expense['start_date']
    frequency = expense['frequency']
    
    if check_date < start_date:
        return False
    
    if frequency == 'daily':
        return True
    elif frequency == 'weekly':
        # Check if it's the same day of the week
        return (check_date - start_date).days % 7 == 0
    elif frequency == 'monthly':
        # Check if it's the same day of the month
        return check_date.day == start_date.day
    else:
        return False

@recurring_expenses_bp.route('/recurring-expenses/process', methods=['POST'])
@require_auth
def manual_process_recurring_expenses():
    """Manually trigger processing of recurring expenses"""
    try:
        processed_count = process_recurring_expenses()
        return jsonify({
            'success': True,
            'message': f'Processed {processed_count} recurring expenses',
            'processed_count': processed_count
        })
    except Exception as e:
        logger.error(f"Error in manual processing: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500
