from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables (for local development)
load_dotenv()

app = Flask(__name__)
CORS(app)

# Custom exception for database connection errors
class DatabaseConnectionError(Exception):
    pass

# Configuration from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")
BUDGET = float(os.environ.get("DAILY_BUDGET", "30.0"))  # Daily budget amount
PORT = int(os.environ.get("PORT", "5001"))  # Server port
DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"  # Debug mode

def get_db_connection():
    """Get a database connection with dict cursor for easy column access"""
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def run_query(sql, params=None, fetch_one=False, fetch_all=True):
    """
    Helper function to run database queries with proper connection handling
    
    Args:
        sql (str): SQL query string
        params (tuple): Query parameters  
        fetch_one (bool): Return single row
        fetch_all (bool): Return all rows (default)
    
    Returns:
        dict or list: Query results as dictionaries
    """
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            
            if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')):
                conn.commit()
                # Check if query has RETURNING clause
                if 'RETURNING' in sql.upper():
                    if fetch_one:
                        result = cur.fetchone()
                        return dict(result) if result else None
                    elif fetch_all:
                        results = cur.fetchall()
                        return [dict(row) for row in results]
                    else:
                        return cur.fetchone()
                else:
                    return cur.rowcount
            elif fetch_one:
                result = cur.fetchone()
                return dict(result) if result else None
            elif fetch_all:
                results = cur.fetchall()
                return [dict(row) for row in results]
            else:
                return None
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Database connection error: {e}")
        raise DatabaseConnectionError(f"Database unavailable: {e}")
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()

# Helper: Get the start and end of the target day (using dayOffset)
def get_day_bounds(day_offset=0):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target_day = today + timedelta(days=day_offset)
    start = target_day
    end = target_day + timedelta(days=1)
    return start, end

# Helper: Get all expenses between two datetimes with optional category filtering
def get_expenses_between(start, end, category_id=None):
    if category_id:
        # Filter by specific category
        sql = '''
            SELECT e.amount, e.description, e.timestamp, e.category_id,
                   c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.user_id = 0 AND e.timestamp >= %s AND e.timestamp < %s AND e.category_id = %s
            ORDER BY e.timestamp DESC
        '''
        params = (start.isoformat(), end.isoformat(), category_id)
    else:
        # Get all expenses with category information
        sql = '''
            SELECT e.amount, e.description, e.timestamp, e.category_id,
                   c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.user_id = 0 AND e.timestamp >= %s AND e.timestamp < %s
            ORDER BY e.timestamp DESC
        '''
        params = (start.isoformat(), end.isoformat())
    
    raw_expenses = run_query(sql, params)
    
    # Convert data types for consistency
    expenses = []
    for e in raw_expenses:
        expense_data = {
            'amount': float(e['amount']),
            'description': e['description'],
            'timestamp': e['timestamp'].isoformat() if hasattr(e['timestamp'], 'isoformat') else str(e['timestamp'])
        }
        
        # Add category information if present
        if e['category_id']:
            expense_data['category'] = {
                'id': e['category_id'],
                'name': e['category_name'],
                'icon': e['category_icon'],
                'color': e['category_color']
            }
        else:
            expense_data['category'] = None
            
        expenses.append(expense_data)
    
    return expenses

@app.route('/health')
def health():
    return {'status': 'ok'}

# Error handlers for database connection issues
@app.errorhandler(DatabaseConnectionError)
def handle_database_error(e):
    """Return JSON error response when database is unavailable"""
    return jsonify({
        'error': 'Database unavailable',
        'message': 'The application is running but the database connection failed. This is normal in demo mode.',
        'demo_mode': True
    }), 503

# Global error handler to ensure all errors return JSON
@app.errorhandler(500)
def handle_internal_error(e):
    """Return JSON error response for internal server errors"""
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again.',
        'demo_mode': True
    }), 500

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    # Get dayOffset from query string (?dayOffset=N), default to 0 (today)
    day_offset = int(request.args.get('dayOffset', 0))
    start, end = get_day_bounds(day_offset)
    
    sql = '''
        SELECT id, amount, description, timestamp 
        FROM expenses 
        WHERE user_id = 0 AND timestamp >= %s AND timestamp < %s 
        ORDER BY timestamp DESC
    '''
    raw_expenses = run_query(sql, (start.isoformat(), end.isoformat()))
    
    # Convert data types for consistent API response
    expenses = []
    for e in raw_expenses:
        expenses.append({
            'id': e['id'],
            'amount': float(e['amount']),
            'description': e['description'],
            'timestamp': e['timestamp'].isoformat() if hasattr(e['timestamp'], 'isoformat') else str(e['timestamp'])
        })
    
    return jsonify(expenses)

@app.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories for the current user"""
    try:
        user_id = 0  # Default user for now - will be updated when auth is fully implemented
        
        sql = '''
            SELECT id, name, icon, color, is_default, daily_budget, created_at
            FROM categories 
            WHERE user_id = %s
            ORDER BY is_default DESC, name ASC
        '''
        categories = run_query(sql, (user_id,), fetch_all=True)
        
        # Convert data types for consistent API response
        result = []
        for cat in categories:
            result.append({
                'id': cat['id'],
                'name': cat['name'],
                'icon': cat['icon'],
                'color': cat['color'],
                'is_default': bool(cat['is_default']),
                'daily_budget': float(cat['daily_budget']) if cat['daily_budget'] else 0.0,
                'created_at': cat['created_at'].isoformat() if hasattr(cat['created_at'], 'isoformat') else str(cat['created_at'])
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
def create_category():
    """Create a new category for the current user"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        icon = data.get('icon', '📝').strip()
        color = data.get('color', '#6B7280').strip()
        user_id = 0  # Default user for now - will be updated when auth is fully implemented
        
        if not name:
            return jsonify({'error': 'Category name is required'}), 400
        
        # Check if category name already exists for this user
        check_sql = 'SELECT id FROM categories WHERE name = %s AND user_id = %s'
        existing = run_query(check_sql, (name, user_id), fetch_one=True)
        if existing:
            return jsonify({'error': 'Category name already exists'}), 409
        
        # Insert new category
        sql = '''
            INSERT INTO categories (name, icon, color, is_default, daily_budget, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, name, icon, color, is_default, daily_budget, created_at
        '''
        new_category = run_query(sql, (name, icon, color, False, 0.0, user_id), fetch_one=True)
        
        result = {
            'id': new_category['id'],
            'name': new_category['name'],
            'icon': new_category['icon'],
            'color': new_category['color'],
            'is_default': bool(new_category['is_default']),
            'daily_budget': float(new_category['daily_budget']),
            'created_at': new_category['created_at'].isoformat() if hasattr(new_category['created_at'], 'isoformat') else str(new_category['created_at'])
        }
        
        return jsonify(result), 201
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/categories/<int:category_id>/budget', methods=['PUT', 'POST'])
def update_category_budget(category_id):
    """Update daily budget for a specific category"""
    try:
        data = request.get_json()
        daily_budget = data.get('daily_budget')
        user_id = 0  # Default user for now - will be updated when auth is fully implemented
        
        if daily_budget is None:
            return jsonify({
                'error': 'daily_budget is required',
                'success': False
            }), 400
        
        try:
            daily_budget = float(daily_budget)
            if daily_budget < 0:
                return jsonify({
                    'error': 'daily_budget must be positive or zero',
                    'success': False
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                'error': 'daily_budget must be a valid number',
                'success': False
            }), 400
        
        # Check if category exists and belongs to the user
        check_sql = 'SELECT id, name FROM categories WHERE id = %s AND user_id = %s'
        category = run_query(check_sql, (category_id, user_id), fetch_one=True)
        if not category:
            return jsonify({
                'error': 'Category not found',
                'success': False
            }), 404
        
        # Update category budget
        sql = '''
            UPDATE categories 
            SET daily_budget = %s 
            WHERE id = %s
            RETURNING id, name, daily_budget
        '''
        result = run_query(sql, (daily_budget, category_id), fetch_one=True)
        
        if result:
            return jsonify({
                'category_id': result['id'],
                'category_name': result['name'],
                'daily_budget': float(result['daily_budget']),
                'success': True,
                'message': f"Budget for {result['name']} updated to ${float(result['daily_budget']):.2f}/day"
            })
        else:
            return jsonify({
                'error': 'Failed to update category budget',
                'success': False
            }), 500
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/categories/budgets', methods=['PUT', 'POST'])
def update_multiple_category_budgets():
    """Update daily budgets for multiple categories at once"""
    try:
        data = request.get_json()
        budgets = data.get('budgets', {})
        
        if not budgets or not isinstance(budgets, dict):
            return jsonify({
                'error': 'budgets object is required (format: {"category_id": daily_budget})',
                'success': False
            }), 400
        
        updated_categories = []
        errors = []
        
        for category_id_str, daily_budget in budgets.items():
            try:
                category_id = int(category_id_str)
                daily_budget = float(daily_budget)
                
                if daily_budget < 0:
                    errors.append(f"Category {category_id}: budget must be positive or zero")
                    continue
                
                # Check if category exists and update
                sql = '''
                    UPDATE categories 
                    SET daily_budget = %s 
                    WHERE id = %s
                    RETURNING id, name, daily_budget
                '''
                result = run_query(sql, (daily_budget, category_id), fetch_one=True)
                
                if result:
                    updated_categories.append({
                        'category_id': result['id'],
                        'category_name': result['name'],
                        'daily_budget': float(result['daily_budget'])
                    })
                else:
                    errors.append(f"Category {category_id}: not found")
                    
            except (ValueError, TypeError):
                errors.append(f"Category {category_id_str}: invalid budget value")
            except Exception as e:
                errors.append(f"Category {category_id_str}: {str(e)}")
        
        if updated_categories:
            response = {
                'updated_categories': updated_categories,
                'success': True,
                'message': f"Updated budgets for {len(updated_categories)} categories"
            }
            if errors:
                response['warnings'] = errors
            return jsonify(response)
        else:
            return jsonify({
                'error': 'No categories were updated',
                'errors': errors,
                'success': False
            }), 400
            
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/categories/budget-tracking', methods=['GET'])
def get_category_budget_tracking():
    """Get category budget tracking for today - spending vs. budget for each category"""
    try:
        day_offset = int(request.args.get('dayOffset', 0))
        today_start, today_end = get_day_bounds(day_offset)
        user_id = 0  # Default user for now - will be updated when auth is fully implemented
        
        # Get all categories with their budgets for the current user
        categories_sql = '''
            SELECT id, name, icon, color, daily_budget
            FROM categories 
            WHERE user_id = %s
            ORDER BY is_default DESC, name ASC
        '''
        categories = run_query(categories_sql, (user_id,), fetch_all=True)
        
        # Get today's spending by category
        spending_sql = '''
            SELECT e.category_id, SUM(e.amount) as total_spent
            FROM expenses e
            WHERE e.user_id = 0 AND e.timestamp >= %s AND e.timestamp < %s
            GROUP BY e.category_id
        '''
        spending_data = run_query(spending_sql, (today_start.isoformat(), today_end.isoformat()))
        
        # Create spending lookup
        spending_by_category = {row['category_id']: float(row['total_spent']) for row in spending_data}
        
        # Separate budgeted and unbedgeted categories
        budgeted_categories = []
        unbedgeted_categories = []
        total_budget = 0
        total_spent_budgeted = 0
        total_spent_unbedgeted = 0
        
        for cat in categories:
            budget = float(cat['daily_budget']) if cat['daily_budget'] else 0.0
            spent = spending_by_category.get(cat['id'], 0.0)
            
            category_data = {
                'category_id': cat['id'],
                'category_name': cat['name'],
                'category_icon': cat['icon'],
                'category_color': cat['color'],
                'spent_today': spent
            }
            
            if budget > 0:
                # This category has a budget
                remaining = budget - spent
                total_budget += budget
                total_spent_budgeted += spent
                
                category_data.update({
                    'daily_budget': budget,
                    'remaining_today': remaining,
                    'percentage_used': (spent / budget * 100),
                    'is_over_budget': spent > budget
                })
                budgeted_categories.append(category_data)
            else:
                # This category has no budget
                total_spent_unbedgeted += spent
                unbedgeted_categories.append(category_data)
        
        return jsonify({
            'budgeted_categories': budgeted_categories,
            'unbedgeted_categories': unbedgeted_categories,
            'summary': {
                'total_budget': total_budget,
                'total_spent_budgeted': total_spent_budgeted,
                'total_spent_unbedgeted': total_spent_unbedgeted,
                'total_spent_all': total_spent_budgeted + total_spent_unbedgeted,
                'total_remaining': total_budget - total_spent_budgeted,
                'overall_percentage_used': (total_spent_budgeted / total_budget * 100) if total_budget > 0 else 0,
                'budgeted_categories_count': len(budgeted_categories),
                'unbedgeted_categories_count': len(unbedgeted_categories)
            },
            'success': True
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    amount = data.get('amount')
    description = data.get('description', '')
    category_id = data.get('category_id')  # New: category selection
    
    if amount is None:
        return jsonify({'error': 'Amount is required'}), 400
    
    # Validate category_id is required
    if not category_id:
        return jsonify({'error': 'Category is required'}), 400
    
    try:
        category_id = int(category_id)
        # Check if category exists
        check_sql = 'SELECT id FROM categories WHERE id = %s'
        category_exists = run_query(check_sql, (category_id,), fetch_one=True)
        if not category_exists:
            return jsonify({'error': 'Invalid category'}), 400
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid category ID'}), 400
    
    # Use local timezone-aware timestamp to ensure consistent date handling
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    sql = '''
        INSERT INTO expenses (user_id, amount, description, category_id, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    '''
    run_query(sql, (0, amount, description, category_id, timestamp), fetch_all=False)
    return jsonify({'success': True}), 201

@app.route('/api/summary', methods=['GET'])
def get_summary():
    day_offset = int(request.args.get('dayOffset', 0))
    today_start, today_end = get_day_bounds(day_offset)
    
    # Calculate daily surplus for the last 7 days
    deltas = []
    for i in range(7):
        offset = day_offset - i
        day_start, day_end = get_day_bounds(offset)
        expenses = get_expenses_between(day_start, day_end)
        total_spent = sum(e['amount'] for e in expenses)
        daily_surplus = get_user_daily_limit(0) - total_spent # Use user's daily limit
        deltas.append(daily_surplus)
    
    # Today's balance and averages
    today_balance = deltas[0]
    avg_daily_surplus = sum(deltas) / 7  # Always divide by 7 days
    projection_30 = avg_daily_surplus * 30  # 30-day projection based on average daily surplus
    
    # Plant state logic based on average daily surplus
    if avg_daily_surplus >= 2:
        plant = 'thriving'
        plant_emoji = '🌳'
    elif avg_daily_surplus >= -2:
        plant = 'healthy'
        plant_emoji = '🌱'
    elif avg_daily_surplus >= -5:
        plant = 'wilting'
        plant_emoji = '🥀'
    else:
        plant = 'dead'
        plant_emoji = '☠️'
    
    return jsonify({
        'balance': round(today_balance, 2),
        'avg_7day': round(avg_daily_surplus, 2),
        'projection_30': round(projection_30, 2),
        'plant_state': plant,
        'plant_emoji': plant_emoji
    })

@app.route('/api/history', methods=['GET'])
def get_history():
    # Get all expenses from the last 7 days (including today)
    day_offset = int(request.args.get('dayOffset', 0))
    period = int(request.args.get('period', 7))  # Default to 7 days
    category_id = request.args.get('category_id')  # Optional category filter
    
    start_date, _ = get_day_bounds(day_offset - (period - 1))
    _, end_date = get_day_bounds(day_offset)
    expenses = get_expenses_between(start_date, end_date, category_id)
    # Group by date (YYYY-MM-DD)
    grouped = {}
    for e in expenses:
        date = e['timestamp'][:10]  # 'YYYY-MM-DD' (timestamp is already a string from helper)
        if date not in grouped:
            grouped[date] = []
        expense_data = {
            'amount': e['amount'],  # Already converted to float in helper
            'description': e['description'],
            'timestamp': e['timestamp']  # Already converted to string in helper
        }
        
        # Add category information if present
        if e.get('category'):
            expense_data['category'] = e['category']
        else:
            expense_data['category'] = None
            
        grouped[date].append(expense_data)
    # Sort by date descending
    grouped_sorted = [
        {'date': date, 'expenses': grouped[date]}
        for date in sorted(grouped.keys(), reverse=True)
    ]
    return jsonify(grouped_sorted)

# Helper function to get user's daily spending limit
def get_user_daily_limit(user_id=0):
    """Get the user's daily spending limit from preferences"""
    try:
        sql = 'SELECT daily_spending_limit FROM user_preferences WHERE user_id = %s'
        result = run_query(sql, (user_id,), fetch_one=True)
        if result:
            return float(result['daily_spending_limit'])
        else:
            # If no preference found, create default and return it
            sql = '''
                INSERT INTO user_preferences (user_id, daily_spending_limit)
                VALUES (%s, %s)
                RETURNING daily_spending_limit
            '''
            result = run_query(sql, (user_id, 30.0), fetch_one=True)
            return float(result['daily_spending_limit']) if result else 30.0
    except Exception as e:
        print(f"Error getting user daily limit: {e}")
        return 30.0  # Fallback to default

@app.route('/api/preferences/daily-limit', methods=['GET'])
def get_daily_limit():
    """Get the user's current daily spending limit"""
    try:
        user_id = 0  # Default user for now
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

@app.route('/api/preferences/daily-limit', methods=['POST', 'PUT'])
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
        
        user_id = 0  # Default user for now
        
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

# Get the frontend directory path relative to this file
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')

@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/history.html')
def serve_history():
    return send_from_directory(FRONTEND_DIR, 'history.html')

@app.route('/settings.html')
def serve_settings():
    return send_from_directory(FRONTEND_DIR, 'settings.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(FRONTEND_DIR, filename)

if __name__ == '__main__':
    # Only run the development server if this file is run directly
    # In production, gunicorn will import and run the app
    app.run(debug=DEBUG, port=PORT, host='0.0.0.0') 