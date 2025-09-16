from flask import Blueprint, request, jsonify
from datetime import datetime, timezone

from utils import (
    logger, run_query, validate_expense_data, handle_errors, 
    get_day_bounds, get_expenses_between, get_user_daily_limit,
    ValidationError
)
from auth import require_auth, get_current_user_id

# Create Blueprint for expense routes
expenses_bp = Blueprint('expenses', __name__)

@expenses_bp.route('/expenses', methods=['GET'])
@require_auth
def get_expenses():
    """Get expenses for a specific day"""
    # Get dayOffset from query string (?dayOffset=N), default to 0 (today)
    day_offset = int(request.args.get('dayOffset', 0))
    user_id = get_current_user_id()
    start, end = get_day_bounds(day_offset, user_id)
    sql = '''
        SELECT id, amount, description, timestamp 
        FROM expenses 
        WHERE user_id = %s AND timestamp >= %s AND timestamp < %s 
        ORDER BY timestamp DESC
    '''
    raw_expenses = run_query(sql, (user_id, start.isoformat(), end.isoformat()))
    
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

@expenses_bp.route('/expenses', methods=['POST'])
@require_auth
@handle_errors
def add_expense():
    """Add a new expense"""
    logger.info("Add expense request received")
    
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    validated_data = validate_expense_data(data)
    amount = validated_data['amount']
    description = validated_data['description']
    category_id = data.get('category_id')  # Category validation handled separately
    
    user_id = get_current_user_id()
    logger.debug("Processing expense for user", extra={'user_id': user_id})
    
    # Check user's category requirement preference
    sql = 'SELECT require_categories FROM user_preferences WHERE user_id = %s'
    result = run_query(sql, (user_id,), fetch_one=True)
    require_categories = result['require_categories'] if result else True  # Default to True
    logger.debug("User category preference retrieved", extra={
        'user_id': user_id,
        'require_categories': require_categories
    })
    
    # Validate category_id based on user preference
    if require_categories and not category_id:
        logger.warning("Category ID missing but categories are required", extra={
            'user_id': user_id,
            'require_categories': require_categories
        })
        raise ValidationError("Category is required", field="category_id")
    elif not require_categories and not category_id:
        logger.info("Category ID missing but categories are optional, proceeding without category", extra={
            'user_id': user_id
        })
        category_id = None
    
    # Initialize category_type
    category_type = None
    
    # Validate category_id if provided
    if category_id:
        # Parse category ID (format: "default_123" or "custom_456")
        if isinstance(category_id, str) and '_' in category_id:
            category_type, cat_id = category_id.split('_', 1)
            numeric_id = int(cat_id)
        else:
            # Legacy format - assume it's a custom category
            numeric_id = int(category_id)
            category_type = 'custom'
        
        logger.debug("Validating category", extra={
            'user_id': user_id,
            'category_type': category_type,
            'numeric_id': numeric_id
        })
        
        if category_type == 'default':
            # Check if default category exists
            check_sql = 'SELECT id FROM default_categories WHERE id = %s'
            category_exists = run_query(check_sql, (numeric_id,), fetch_one=True)
        else:
            # Check if custom category exists and belongs to the user
            check_sql = 'SELECT id FROM custom_categories WHERE id = %s AND user_id = %s'
            category_exists = run_query(check_sql, (numeric_id, user_id), fetch_one=True)
        
        if not category_exists:
            logger.warning("Invalid category provided", extra={
                'user_id': user_id,
                'category_type': category_type,
                'numeric_id': numeric_id
            })
            raise ValidationError("Invalid category", field="category_id")
        logger.debug("Category validated successfully", extra={
            'user_id': user_id,
            'category_type': category_type,
            'numeric_id': numeric_id
        })
    else:
        logger.info("No category provided, expense will be saved without category", extra={
            'user_id': user_id
        })
    
    # Use UTC timestamp to ensure consistent date handling across timezones
    # Check if user has a simulated date set
    simulated_date_result = run_query("""
        SELECT simulated_date 
        FROM user_preferences 
        WHERE user_id = %s AND simulated_date IS NOT NULL
    """, (user_id,), fetch_one=True)
    
    if simulated_date_result and simulated_date_result['simulated_date']:
        # Use simulated date for the timestamp
        simulated_date = simulated_date_result['simulated_date']
        # Create timestamp with simulated date but current time
        current_time = datetime.now(timezone.utc).time()
        timestamp = datetime.combine(simulated_date, current_time).strftime('%Y-%m-%d %H:%M:%S')
        logger.debug("Using simulated date for expense timestamp", extra={
            'user_id': user_id,
            'simulated_date': simulated_date,
            'timestamp': timestamp
        })
    else:
        # Use current UTC timestamp
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        logger.debug("Using current UTC timestamp for expense", extra={
            'user_id': user_id,
            'timestamp': timestamp
        })
    
    logger.info("Inserting expense into database", extra={
        'user_id': user_id,
        'amount': amount,
        'description': description
    })
    
    # Convert category_id back to the full string format for storage
    if category_id:
        if category_type == 'default':
            storage_category_id = f"default_{numeric_id}"
        else:
            storage_category_id = f"custom_{numeric_id}"
    else:
        storage_category_id = None
    
    sql = '''
        INSERT INTO expenses (user_id, amount, description, category_id, timestamp)
        VALUES (%s, %s, %s, %s, %s)
    '''
    result = run_query(sql, (user_id, amount, description, storage_category_id, timestamp), fetch_all=False)
    logger.info("Expense inserted successfully", extra={
        'user_id': user_id,
        'expense_id': result,
        'category_id': storage_category_id,
        'amount': amount
    })
    return jsonify({'success': True}), 201

@expenses_bp.route('/summary', methods=['GET'])
@require_auth
def get_summary():
    """Get spending summary and plant state"""
    try:
        day_offset = int(request.args.get('dayOffset', 0))
        user_id = get_current_user_id()
        today_start, today_end = get_day_bounds(day_offset, user_id)
        
        # Get user's daily limit with fallback
        try:
            user_daily_limit = get_user_daily_limit(user_id)
        except Exception as e:
            logger.error(f"Error getting user daily limit: {e}, using default")
            user_daily_limit = 30.0
        
        # OPTIMIZED: Get 7-day spending data in a single query
        start_date, _ = get_day_bounds(day_offset - 6, user_id)  # 7 days ago
        _, end_date = get_day_bounds(day_offset + 1, user_id)    # Tomorrow
        
        try:
            # Single query to get daily spending for the last 7 days
            summary_sql = '''
                SELECT 
                    DATE(timestamp) as date,
                    SUM(amount) as daily_total
                FROM expenses 
                WHERE user_id = %s 
                AND timestamp >= %s 
                AND timestamp < %s
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            '''
            
            daily_spending = run_query(summary_sql, (user_id, start_date.isoformat(), end_date.isoformat()), fetch_all=True)
            
            # Create a lookup for daily spending
            spending_lookup = {}
            for day in daily_spending:
                spending_lookup[day['date'].strftime('%Y-%m-%d')] = float(day['daily_total'])
            
            # Calculate daily surplus for the last 7 days
            deltas = []
            for i in range(7):
                offset = day_offset - i
                day_start, day_end = get_day_bounds(offset, user_id)
                date_key = day_start.strftime('%Y-%m-%d')
                daily_spent = spending_lookup.get(date_key, 0.0)
                daily_surplus = user_daily_limit - daily_spent
                deltas.append(daily_surplus)
                
        except Exception as e:
            logger.error(f"Error getting 7-day spending data: {e}, using defaults")
            # Fallback to default values
            deltas = [user_daily_limit] * 7
        
        # Today's balance and averages
        today_balance = deltas[0] if deltas else user_daily_limit
        avg_daily_surplus = sum(deltas) / 7 if deltas else user_daily_limit  # Always divide by 7 days
        
        # Plant state logic - prioritize today's spending over 7-day average
        if today_balance < 0:
            # Today's spending exceeded the daily limit
            if today_balance >= -5:
                plant = 'wilting'
                plant_emoji = '🥀'
            else:
                plant = 'dead'
                plant_emoji = '☠️'
        elif today_balance >= 10 and avg_daily_surplus >= 2:
            plant = 'thriving'
            plant_emoji = '🌳'
        elif today_balance >= 0 and avg_daily_surplus >= -2:
            plant = 'healthy'
            plant_emoji = '🌱'
        else:
            plant = 'struggling'
            plant_emoji = '🌿'
        
        return jsonify({
            'balance': round(today_balance, 2),
            'avg_7day': round(avg_daily_surplus, 2),
            'daily_limit': user_daily_limit,
            'plant_state': plant,
            'plant_emoji': plant_emoji
        })
        
    except Exception as e:
        logger.error(f"Summary endpoint error: {e}")
        
        # Return a safe fallback response instead of crashing
        return jsonify({
            'balance': 30.0,
            'avg_7day': 30.0,
            'daily_limit': 30.0,
            'plant_state': 'healthy',
            'plant_emoji': '🌱'
        })

@expenses_bp.route('/history', methods=['GET'])
@require_auth
def get_history():
    """Get expense history grouped by date"""
    try:
        # Get all expenses from the last 7 days (including today)
        day_offset = int(request.args.get('dayOffset', 0))
        period = int(request.args.get('period', 7))  # Default to 7 days
        category_id = request.args.get('category_id')  # Optional category filter
        
        user_id = get_current_user_id()
        start_date, _ = get_day_bounds(day_offset - (period - 1), user_id)
        _, end_date = get_day_bounds(day_offset, user_id)
        
        try:
            expenses = get_expenses_between(start_date, end_date, user_id, category_id)
        except Exception as e:
            logger.error(f"Error getting expenses: {e}")
            # Return empty history instead of crashing
            return jsonify([])
        
        # Group by date (YYYY-MM-DD)
        grouped = {}
        for e in expenses:
            date = e['timestamp'][:10]  # 'YYYY-MM-DD' (timestamp is already a string from helper)
            if date not in grouped:
                grouped[date] = []
            expense_data = {
                'id': e['id'],  # Add the expense ID for edit/delete functionality
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
        
    except Exception as e:
        logger.error(f"History endpoint error: {e}")
        # Return empty history instead of crashing
        return jsonify([])

@expenses_bp.route('/expenses/<int:expense_id>', methods=['PUT', 'POST'])
@require_auth
@handle_errors
def update_expense(expense_id):
    """Update an existing expense"""
    logger.info(f"Update expense request received for expense {expense_id}")
    
    if not request.is_json:
        raise ValidationError("Request must be JSON")
    
    data = request.get_json()
    logger.debug(f"Update data received: {data}")
    
    try:
        validated_data = validate_expense_data(data)
        amount = validated_data['amount']
        description = validated_data['description']
        category_id = data.get('category_id')
        
        user_id = get_current_user_id()
        logger.debug(f"Processing expense update for user {user_id}, expense {expense_id}")
        
        # First, verify the expense exists and belongs to the user
        check_sql = 'SELECT id FROM expenses WHERE id = %s AND user_id = %s'
        existing_expense = run_query(check_sql, (expense_id, user_id), fetch_one=True)
        
        if not existing_expense:
            logger.warning(f"Expense {expense_id} not found or doesn't belong to user {user_id}")
            raise ValidationError("Expense not found or access denied")
        
        # Validate category_id if provided
        storage_category_id = None
        if category_id:
            logger.debug(f"Processing category_id: {category_id}")
            # Parse category ID (format: "default_123" or "custom_456")
            if isinstance(category_id, str) and '_' in category_id:
                category_type, cat_id = category_id.split('_', 1)
                numeric_id = int(cat_id)
            else:
                # Legacy format - assume it's a custom category
                numeric_id = int(category_id)
                category_type = 'custom'
            
            logger.debug(f"Parsed category - type: {category_type}, numeric_id: {numeric_id}")
            
            # Validate the category exists and belongs to the user
            if category_type == 'default':
                check_sql = 'SELECT id FROM default_categories WHERE id = %s'
                category_exists = run_query(check_sql, (numeric_id,), fetch_one=True)
            else:
                check_sql = 'SELECT id FROM custom_categories WHERE id = %s AND user_id = %s'
                category_exists = run_query(check_sql, (numeric_id, user_id), fetch_one=True)
            
            if not category_exists:
                logger.warning(f"Invalid category {numeric_id} provided for expense update")
                raise ValidationError("Invalid category", field="category_id")
            
            # Convert category_id back to the full string format for storage
            if category_type == 'default':
                storage_category_id = f"default_{numeric_id}"
            else:
                storage_category_id = f"custom_{numeric_id}"
            
            logger.debug(f"Final storage_category_id: {storage_category_id}")
        
        # Update the expense
        update_sql = '''
            UPDATE expenses 
            SET amount = %s, description = %s, category_id = %s
            WHERE id = %s AND user_id = %s
        '''
        
        logger.debug(f"Executing update SQL with params: amount={amount}, description={description}, category_id={storage_category_id}, expense_id={expense_id}, user_id={user_id}")
        
        result = run_query(update_sql, (amount, description, storage_category_id, expense_id, user_id), fetch_all=False)
        
        logger.debug(f"Update result: {result}")
        
        if result == 0:
            logger.error(f"No rows updated for expense {expense_id}")
            raise ValidationError("Failed to update expense")
        
        logger.info(f"Expense {expense_id} updated successfully for user {user_id}")
        return jsonify({'success': True, 'message': 'Expense updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating expense {expense_id}: {str(e)}", exc_info=True)
        raise ValidationError(f"Failed to update expense: {str(e)}")

@expenses_bp.route('/expenses/<int:expense_id>', methods=['DELETE'])
@require_auth
@handle_errors
def delete_expense(expense_id):
    """Delete an existing expense"""
    logger.info(f"Delete expense request received for expense {expense_id}")
    
    user_id = get_current_user_id()
    logger.debug(f"Processing expense deletion for user {user_id}, expense {expense_id}")
    
    # First, verify the expense exists and belongs to the user
    check_sql = 'SELECT id FROM expenses WHERE id = %s AND user_id = %s'
    existing_expense = run_query(check_sql, (expense_id, user_id), fetch_one=True)
    
    if not existing_expense:
        logger.warning(f"Expense {expense_id} not found or doesn't belong to user {user_id}")
        raise ValidationError("Expense not found or access denied")
    
    # Delete the expense
    delete_sql = 'DELETE FROM expenses WHERE id = %s AND user_id = %s'
    result = run_query(delete_sql, (expense_id, user_id), fetch_all=False)
    
    if result == 0:
        logger.error(f"No rows deleted for expense {expense_id}")
        raise ValidationError("Failed to delete expense")
    
    logger.info(f"Expense {expense_id} deleted successfully for user {user_id}")
    return jsonify({'success': True, 'message': 'Expense deleted successfully'})

@expenses_bp.route('/analytics/daily-spending', methods=['GET'])
@require_auth
@handle_errors
def get_daily_spending_analytics():
    """Get daily spending analytics with clean, simple implementation"""
    try:
        user_id = get_current_user_id()
        days = int(request.args.get('days', 30))
        day_offset = int(request.args.get('dayOffset', 0))
        
        # Get user's daily budget limit
        user_daily_limit = get_user_daily_limit(user_id)
        
        # Use the same date calculation logic as the main app
        from datetime import datetime, timedelta, timezone
        
        # Get the current "today" using the same logic as get_day_bounds
        if user_id:
            try:
                # First check if the simulated_date column exists
                column_check = run_query("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'user_preferences' 
                    AND column_name = 'simulated_date'
                """, fetch_one=True)
                
                if column_check:
                    simulated_date_result = run_query("""
                        SELECT simulated_date 
                        FROM user_preferences 
                        WHERE user_id = %s AND simulated_date IS NOT NULL
                    """, (user_id,), fetch_one=True)
                    
                    if simulated_date_result and simulated_date_result['simulated_date']:
                        # Use simulated date as the base
                        simulated_date = simulated_date_result['simulated_date']
                        target_day = datetime.combine(simulated_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                        target_day = target_day + timedelta(days=day_offset)
                        today = target_day.date()
                    else:
                        # Use real current date
                        today = datetime.now(timezone.utc).date() + timedelta(days=day_offset)
                else:
                    # Column doesn't exist, use real current date
                    today = datetime.now(timezone.utc).date() + timedelta(days=day_offset)
            except Exception as e:
                logger.warning(f"Could not check simulated date for user {user_id}: {e}")
                today = datetime.now(timezone.utc).date() + timedelta(days=day_offset)
        else:
            today = datetime.now(timezone.utc).date() + timedelta(days=day_offset)
        
        logger.info(f"Analytics date calculation: day_offset={day_offset}, today={today}")
        
        start_date = today - timedelta(days=days-1)
        
        # Get all expenses in the date range using the same approach as the main app
        # We'll get expenses for each day individually to ensure proper timezone handling
        all_expenses = []
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            day_start, day_end = get_day_bounds(day_offset - (days-1-i), user_id)
            
            sql = '''
                SELECT 
                    amount,
                    description,
                    timestamp
                FROM expenses 
                WHERE user_id = %s 
                    AND timestamp >= %s 
                    AND timestamp < %s
                ORDER BY timestamp ASC
            '''
            
            day_expenses = run_query(sql, (user_id, day_start.isoformat(), day_end.isoformat()))
            
            # Add date information to each expense
            for expense in day_expenses:
                expense['expense_date'] = current_date
                all_expenses.append(expense)
        
        logger.info(f"Analytics query: start_date={start_date}, today={today}, found {len(all_expenses)} expenses")
        
        # Group expenses by date
        daily_totals = {}
        for expense in all_expenses:
            date_str = expense['expense_date'].strftime('%Y-%m-%d')
            logger.info(f"Processing expense: date={date_str}, amount={expense['amount']}, timestamp={expense['timestamp']}")
            if date_str not in daily_totals:
                daily_totals[date_str] = {
                    'amount': 0.0,
                    'count': 0,
                    'expenses': []
                }
            daily_totals[date_str]['amount'] += float(expense['amount'])
            daily_totals[date_str]['count'] += 1
            daily_totals[date_str]['expenses'].append({
                'amount': float(expense['amount']),
                'description': expense['description'],
                'time': expense['timestamp'].strftime('%H:%M')
            })
        
        # Create complete date range with data
        chart_data = []
        total_spent = 0.0
        days_over_budget = 0
        days_with_spending = 0
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            
            if date_str in daily_totals:
                amount = daily_totals[date_str]['amount']
                count = daily_totals[date_str]['count']
                expenses_list = daily_totals[date_str]['expenses']
                days_with_spending += 1
            else:
                amount = 0.0
                count = 0
                expenses_list = []
            
            total_spent += amount
            if amount > user_daily_limit:
                days_over_budget += 1
            
            chart_data.append({
                'date': date_str,
                'amount': amount,
                'count': count,
                'budget_limit': user_daily_limit,
                'expenses': expenses_list
            })
        
        # Calculate summary
        avg_daily = total_spent / days if days > 0 else 0.0
        days_under_budget = days_with_spending - days_over_budget
        days_no_spending = days - days_with_spending
        
        return jsonify({
            'success': True,
            'data': chart_data,
            'summary': {
                'total_days': days,
                'total_spent': round(total_spent, 2),
                'average_daily': round(avg_daily, 2),
                'daily_budget_limit': user_daily_limit,
                'days_over_budget': days_over_budget,
                'days_under_budget': days_under_budget,
                'days_no_spending': days_no_spending,
                'days_with_spending': days_with_spending
            }
        })
        
    except Exception as e:
        logger.error(f"Analytics error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load analytics data',
            'details': str(e) if DEBUG else 'Please try again later'
        }), 500

@expenses_bp.route('/analytics/category-breakdown', methods=['GET'])
@require_auth
@handle_errors
def get_category_breakdown_analytics():
    """Get category spending breakdown analytics"""
    try:
        user_id = get_current_user_id()
        days = int(request.args.get('days', 30))
        day_offset = int(request.args.get('dayOffset', 0))
        
        # Use the same date calculation logic as daily spending analytics
        from datetime import datetime, timedelta, timezone
        from utils import get_day_bounds
        
        # Get the current "today" using the same logic as get_day_bounds
        base_date = datetime.now(timezone.utc).date()
        today_for_range = base_date + timedelta(days=day_offset)
        start_date_for_range = today_for_range - timedelta(days=days-1)
        
        # Get all expenses in the date range
        all_expenses = []
        
        for i in range(days):
            current_date_in_loop = start_date_for_range + timedelta(days=i)
            relative_day_offset = (current_date_in_loop - base_date).days
            
            day_start, day_end = get_day_bounds(relative_day_offset, user_id)
            
            sql = '''
                SELECT
                    e.amount,
                    e.description,
                    e.timestamp,
                    COALESCE(dc.name, cc.name) as category_name,
                    COALESCE(dc.color, cc.color) as category_color
                FROM expenses e
                LEFT JOIN default_categories dc ON e.category_id = CONCAT('default_', dc.id::text)
                LEFT JOIN custom_categories cc ON e.category_id = CONCAT('custom_', cc.id::text) AND cc.user_id = e.user_id
                WHERE e.user_id = %s
                    AND e.timestamp >= %s
                    AND e.timestamp < %s
                ORDER BY e.timestamp ASC
            '''
            
            day_expenses = run_query(sql, (user_id, day_start.isoformat(), day_end.isoformat()))
            
            # Add date information to each expense
            for expense in day_expenses:
                expense['expense_date'] = current_date_in_loop
                all_expenses.append(expense)
        
        # Group expenses by category
        category_totals = {}
        total_spent = 0.0
        
        for expense in all_expenses:
            category_name = expense['category_name'] or 'Uncategorized'
            amount = float(expense['amount'])
            
            if category_name not in category_totals:
                category_totals[category_name] = {
                    'amount': 0.0,
                    'count': 0,
                    'color': expense['category_color'] or '#6c757d',  # Default gray color
                    'expenses': []
                }
            
            category_totals[category_name]['amount'] += amount
            category_totals[category_name]['count'] += 1
            category_totals[category_name]['expenses'].append({
                'amount': amount,
                'description': expense['description'],
                'date': expense['expense_date'].strftime('%Y-%m-%d'),
                'time': expense['timestamp'].strftime('%H:%M')
            })
            total_spent += amount
        
        # Convert to chart data format
        chart_data = []
        for category_name, data in category_totals.items():
            percentage = (data['amount'] / total_spent * 100) if total_spent > 0 else 0
            chart_data.append({
                'category': category_name,
                'amount': round(data['amount'], 2),
                'count': data['count'],
                'percentage': round(percentage, 1),
                'color': data['color'],
                'expenses': data['expenses']
            })
        
        # Sort by amount (highest first)
        chart_data.sort(key=lambda x: x['amount'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': chart_data,
            'summary': {
                'total_categories': len(chart_data),
                'total_spent': round(total_spent, 2),
                'days_analyzed': days
            }
        })
        
    except Exception as e:
        logger.error(f"Category breakdown analytics error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load category breakdown data',
            'details': str(e) if DEBUG else 'Please try again later'
        }), 500

@expenses_bp.route('/analytics/weekly-heatmap', methods=['GET'])
@require_auth
@handle_errors
def get_weekly_heatmap_analytics():
    """Get 30-day spending heatmap analytics - ultra-optimized version"""
    try:
        user_id = get_current_user_id()
        days = int(request.args.get('days', 30))  # Default to 30 days
        day_offset = int(request.args.get('dayOffset', 0))
        
        # Simple cache key for this specific request
        cache_key = f"heatmap_{user_id}_{days}_{day_offset}"
        
        # Check if we have cached data (5 minute cache)
        from datetime import datetime, timedelta, timezone
        cache_timestamp_key = f"{cache_key}_timestamp"
        
        # For now, skip caching to ensure we get the performance improvement
        # TODO: Add proper caching system later
        
        # Performance tracking
        start_time = datetime.now()
        logger.info(f"Heatmap request started for user {user_id}, days={days}, offset={day_offset}")
        
        # Use the same date calculation logic as other analytics
        from datetime import datetime, timedelta, timezone
        from utils import get_day_bounds
        
        # Get the current "today" using the same logic as get_day_bounds
        base_date = datetime.now(timezone.utc).date()
        today_for_range = base_date + timedelta(days=day_offset)
        start_date_for_range = today_for_range - timedelta(days=days-1)
        
        # Ultra-optimized single query with aggregation - no individual expense details needed for heatmap
        overall_start, _ = get_day_bounds(day_offset - (days-1), user_id)
        _, overall_end = get_day_bounds(day_offset + 1, user_id)
        
        # Use database aggregation instead of fetching all individual expenses
        sql = '''
            SELECT
                DATE(timestamp) as expense_date,
                SUM(amount) as daily_total,
                COUNT(*) as transaction_count
            FROM expenses
            WHERE user_id = %s
                AND timestamp >= %s
                AND timestamp < %s
            GROUP BY DATE(timestamp)
            ORDER BY expense_date ASC
        '''
        
        daily_data = run_query(sql, (user_id, overall_start.isoformat(), overall_end.isoformat()))
        
        # Create lookup dictionary for fast access
        daily_lookup = {}
        for day in daily_data:
            date_str = day['expense_date'].strftime('%Y-%m-%d')
            daily_lookup[date_str] = {
                'amount': float(day['daily_total']),
                'count': day['transaction_count']
            }
        
        # Create complete date range with data (much faster)
        all_expenses = []
        for i in range(days):
            current_date = start_date_for_range + timedelta(days=i)
            date_str = current_date.strftime('%Y-%m-%d')
            
            if date_str in daily_lookup:
                day_data = daily_lookup[date_str]
                all_expenses.append({
                    'date': current_date,
                    'amount': day_data['amount'],
                    'count': day_data['count'],
                    'expenses': []  # Empty for heatmap - we don't need individual expenses
                })
            else:
                all_expenses.append({
                    'date': current_date,
                    'amount': 0.0,
                    'count': 0,
                    'expenses': []
                })
        
        # Calculate spending statistics for color intensity
        amounts = [expense['amount'] for expense in all_expenses if expense['amount'] > 0]
        max_spending = max(amounts) if amounts else 0
        avg_spending = sum(amounts) / len(amounts) if amounts else 0
        
        # Ultra-fast heatmap data creation with pre-calculated values
        heatmap_data = []
        
        # Pre-calculate intensity multiplier to avoid division in loop
        intensity_multiplier = 1.0 / max_spending if max_spending > 0 else 0
        
        # Process all days at once
        for i in range(0, len(all_expenses), 7):  # Process 7 days at a time
            week_data = []
            
            for j in range(7):
                if i + j < len(all_expenses):
                    expense = all_expenses[i + j]
                    date = expense['date']
                    amount = expense['amount']
                    count = expense['count']
                    
                    # Fast color level calculation
                    if amount == 0:
                        color_level = 0
                        intensity = 0
                    else:
                        intensity = min(amount * intensity_multiplier, 1.0)
                        if intensity <= 0.25:
                            color_level = 1
                        elif intensity <= 0.5:
                            color_level = 2
                        elif intensity <= 0.75:
                            color_level = 3
                        else:
                            color_level = 4
                    
                    week_data.append({
                        'date': date.strftime('%Y-%m-%d'),
                        'day_name': date.strftime('%a'),
                        'day_number': date.day,
                        'month_name': date.strftime('%b'),
                        'amount': round(amount, 2),
                        'count': count,
                        'intensity': round(intensity, 2),
                        'color_level': color_level,
                        'expenses': []  # Empty for performance
                    })
                else:
                    # Pad with empty day
                    week_data.append({
                        'date': None,
                        'day_name': '',
                        'day_number': '',
                        'month_name': '',
                        'amount': 0,
                        'count': 0,
                        'intensity': 0,
                        'color_level': 0,
                        'expenses': []
                    })
            
            heatmap_data.append(week_data)
        
        # Performance tracking
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        logger.info(f"Heatmap request completed in {processing_time:.2f} seconds for user {user_id}")
        
        return jsonify({
            'success': True,
            'data': heatmap_data,
            'summary': {
                'total_weeks': len(heatmap_data),
                'total_days': days,
                'max_spending': round(max_spending, 2),
                'avg_spending': round(avg_spending, 2),
                'start_date': start_date_for_range.strftime('%Y-%m-%d'),
                'end_date': today_for_range.strftime('%Y-%m-%d'),
                'processing_time_seconds': round(processing_time, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Weekly heatmap analytics error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load heatmap data',
            'details': str(e) if DEBUG else 'Please try again later'
        }), 500

@expenses_bp.route('/analytics/test', methods=['GET'])
@require_auth
@handle_errors
def test_analytics():
    """Test endpoint to verify analytics API is working"""
    try:
        user_id = get_current_user_id()
        logger.info(f"Analytics test endpoint called for user {user_id}")
        
        # Test database connection
        test_query = "SELECT COUNT(*) as count FROM expenses WHERE user_id = %s"
        result = run_query(test_query, (user_id,), fetch_one=True)
        
        return jsonify({
            'success': True,
            'message': 'Analytics API is working',
            'user_id': user_id,
            'expense_count': result['count'] if result else 0,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Analytics test error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Analytics test failed',
            'details': str(e) if DEBUG else 'Please check server logs'
        }), 500

