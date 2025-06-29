from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'db.sqlite3')
BUDGET = 30.0  # Fixed daily budget

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Helper: Get the start and end of the target day (using dayOffset)
def get_day_bounds(day_offset=0):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target_day = today + timedelta(days=day_offset)
    start = target_day
    end = target_day + timedelta(days=1)
    return start, end

# Helper: Get all expenses between two datetimes
def get_expenses_between(start, end):
    conn = get_db_connection()
    cur = conn.execute(
        'SELECT amount, description, timestamp FROM expenses WHERE user_id = 0 AND timestamp >= ? AND timestamp < ? ORDER BY timestamp DESC',
        (start.isoformat(), end.isoformat())
    )
    expenses = [dict(row) for row in cur.fetchall()]
    conn.close()
    return expenses

@app.route('/health')
def health():
    return {'status': 'ok'}

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    # Get dayOffset from query string (?dayOffset=N), default to 0 (today)
    day_offset = int(request.args.get('dayOffset', 0))
    start, end = get_day_bounds(day_offset)
    conn = get_db_connection()
    cur = conn.execute(
        'SELECT id, amount, description, timestamp FROM expenses WHERE user_id = 0 AND timestamp >= ? AND timestamp < ? ORDER BY timestamp DESC',
        (start.isoformat(), end.isoformat())
    )
    expenses = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify(expenses)

@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    amount = data.get('amount')
    description = data.get('description', '')
    if amount is None:
        return jsonify({'error': 'Amount is required'}), 400
    timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO expenses (user_id, amount, description, timestamp) VALUES (?, ?, ?, ?)',
        (0, amount, description, timestamp)
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True}), 201

@app.route('/api/summary', methods=['GET'])
def get_summary():
    day_offset = int(request.args.get('dayOffset', 0))
    today_start, today_end = get_day_bounds(day_offset)
    deltas = []
    days_counted = 0
    for i in range(7):
        offset = day_offset - i
        day_start, day_end = get_day_bounds(offset)
        expenses = get_expenses_between(day_start, day_end)
        total_spent = sum(e['amount'] for e in expenses)
        delta = BUDGET - total_spent
        deltas.append(delta)
        days_counted += 1 if expenses or i == 0 else 0  # Always count today, even if no expenses
    # Only average over days with data, or at least 1 day (today)
    if days_counted == 0:
        days_counted = 1
    today_delta = deltas[0]
    avg_7day = sum(deltas) / days_counted
    projection_30 = avg_7day * 30
    # Plant state logic
    if avg_7day >= 2:
        plant = 'thriving'
        plant_emoji = '🌳'
    elif avg_7day >= -2:
        plant = 'healthy'
        plant_emoji = '🌱'
    elif avg_7day >= -5:
        plant = 'wilting'
        plant_emoji = '🥀'
    else:
        plant = 'dead'
        plant_emoji = '☠️'
    return jsonify({
        'balance': round(today_delta, 2),
        'avg_7day': round(avg_7day, 2),
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
        date = e['timestamp'][:10]  # 'YYYY-MM-DD'
        if date not in grouped:
            grouped[date] = []
        grouped[date].append({
            'amount': e['amount'],
            'description': e['description'],
            'timestamp': e['timestamp']
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
    app.run(debug=True) 