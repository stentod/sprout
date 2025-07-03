from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")
BUDGET = 30.0  # Fixed daily budget

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
                return cur.rowcount
            elif fetch_one:
                result = cur.fetchone()
                return dict(result) if result else None
            elif fetch_all:
                results = cur.fetchall()
                return [dict(row) for row in results]
            else:
                return None
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

# Helper: Get all expenses between two datetimes
def get_expenses_between(start, end):
    sql = '''
        SELECT amount, description, timestamp 
        FROM expenses 
        WHERE user_id = 0 AND timestamp >= %s AND timestamp < %s 
        ORDER BY timestamp DESC
    '''
    raw_expenses = run_query(sql, (start.isoformat(), end.isoformat()))
    
    # Convert data types for consistency
    expenses = []
    for e in raw_expenses:
        expenses.append({
            'amount': float(e['amount']),
            'description': e['description'],
            'timestamp': e['timestamp'].isoformat() if hasattr(e['timestamp'], 'isoformat') else str(e['timestamp'])
        })
    
    return expenses

@app.route('/health')
def health():
    return {'status': 'ok'}

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

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    amount = data.get('amount')
    description = data.get('description', '')
    if amount is None:
        return jsonify({'error': 'Amount is required'}), 400
    timestamp = datetime.now().isoformat()
    
    sql = '''
        INSERT INTO expenses (user_id, amount, description, timestamp) 
        VALUES (%s, %s, %s, %s)
    '''
    run_query(sql, (0, amount, description, timestamp), fetch_all=False)
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
        daily_surplus = BUDGET - total_spent
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
    start_7days, _ = get_day_bounds(day_offset - 6)
    _, end_today = get_day_bounds(day_offset)
    expenses = get_expenses_between(start_7days, end_today)
    # Group by date (YYYY-MM-DD)
    grouped = {}
    for e in expenses:
        date = e['timestamp'][:10]  # 'YYYY-MM-DD' (timestamp is already a string from helper)
        if date not in grouped:
            grouped[date] = []
        grouped[date].append({
            'amount': e['amount'],  # Already converted to float in helper
            'description': e['description'],
            'timestamp': e['timestamp']  # Already converted to string in helper
        })
    # Sort by date descending
    grouped_sorted = [
        {'date': date, 'expenses': grouped[date]}
        for date in sorted(grouped.keys(), reverse=True)
    ]
    return jsonify(grouped_sorted)

@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')

@app.route('/history.html')
def serve_history():
    return send_from_directory('../frontend', 'history.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('../frontend', filename)

if __name__ == '__main__':
    app.run(debug=True, port=5001) 