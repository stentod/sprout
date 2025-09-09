from flask import Blueprint, request, jsonify

from utils import (
    logger, run_query, validate_category_data, handle_errors, 
    get_day_bounds, get_user_daily_limit,
    ValidationError, _cache, _cache_timestamps
)
from auth import require_auth, get_current_user_id

# Create Blueprint for category routes
categories_bp = Blueprint('categories', __name__)

@categories_bp.route('/categories', methods=['GET'])
@require_auth
def get_categories():
    """Get all categories for the current user (default + custom) - OPTIMIZED VERSION"""
    try:
        user_id = get_current_user_id()
        
        try:
            # OPTIMIZED: Single query with UNION to get all categories and budgets
            optimized_sql = '''
                SELECT 
                    'default_' || dc.id as id,
                    dc.name,
                    dc.icon,
                    dc.color,
                    dc.created_at,
                    COALESCE(ucb.daily_budget, 0.0) as daily_budget,
                    true as is_default,
                    false as is_custom
                FROM default_categories dc
                LEFT JOIN user_category_budgets ucb ON ucb.category_id = dc.id AND ucb.category_type = 'default' AND ucb.user_id = %s
                
                UNION ALL
                
                SELECT 
                    'custom_' || cc.id as id,
                    cc.name,
                    cc.icon,
                    cc.color,
                    cc.created_at,
                    COALESCE(ucb.daily_budget, cc.daily_budget) as daily_budget,
                    false as is_default,
                    true as is_custom
                FROM custom_categories cc
                LEFT JOIN user_category_budgets ucb ON ucb.category_id = cc.id AND ucb.category_type = 'custom' AND ucb.user_id = %s
                WHERE cc.user_id = %s
                
                ORDER BY name ASC
            '''
            
            categories_raw = run_query(optimized_sql, (user_id, user_id, user_id), fetch_all=True)
            
            # Format the results
            categories = []
            for cat in categories_raw:
                categories.append({
                    'id': cat['id'],
                    'name': cat['name'],
                    'icon': cat['icon'],
                    'color': cat['color'],
                    'daily_budget': float(cat['daily_budget']),
                    'is_default': cat['is_default'],
                    'is_custom': cat['is_custom'],
                    'created_at': cat['created_at'].isoformat() if hasattr(cat['created_at'], 'isoformat') else str(cat['created_at'])
                })
            
            return jsonify(categories)
            
        except Exception as db_error:
            logger.error(f"Database error getting categories: {db_error}")
            # Return basic default categories if database fails
            return jsonify([
                {
                    'id': 'default_1',
                    'name': 'Food & Dining',
                    'icon': '🍽️',
                    'color': '#FF6B6B',
                    'daily_budget': 0.0,
                    'is_default': True,
                    'is_custom': False
                },
                {
                    'id': 'default_2', 
                    'name': 'Transportation',
                    'icon': '🚗',
                    'color': '#4ECDC4',
                    'daily_budget': 0.0,
                    'is_default': True,
                    'is_custom': False
                },
                {
                    'id': 'default_3',
                    'name': 'Shopping',
                    'icon': '🛒',
                    'color': '#45B7D1',
                    'daily_budget': 0.0,
                    'is_default': True,
                    'is_custom': False
                },
                {
                    'id': 'default_4',
                    'name': 'Health & Fitness',
                    'icon': '💪',
                    'color': '#96CEB4',
                    'daily_budget': 0.0,
                    'is_default': True,
                    'is_custom': False
                },
                {
                    'id': 'default_5',
                    'name': 'Entertainment',
                    'icon': '🎬',
                    'color': '#FECA57',
                    'daily_budget': 0.0,
                    'is_default': True,
                    'is_custom': False
                },
                {
                    'id': 'default_6',
                    'name': 'Bills & Utilities',
                    'icon': '⚡',
                    'color': '#FF9FF3',
                    'daily_budget': 0.0,
                    'is_default': True,
                    'is_custom': False
                },
                {
                    'id': 'default_7',
                    'name': 'Other',
                    'icon': '📝',
                    'color': '#6B7280',
                    'daily_budget': 0.0,
                    'is_default': True,
                    'is_custom': False
                }
            ])
            
    except Exception as e:
        logger.error(f"Error in get_categories: {e}")
        return jsonify({'error': 'Failed to load categories'}), 500

@categories_bp.route('/categories', methods=['POST'])
@require_auth
def create_category():
    """Create a new custom category for the current user"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        name = data.get('name', '').strip()
        icon = data.get('icon', '📦')
        color = data.get('color', '#A9A9A9')
        daily_budget = data.get('daily_budget', 0.0)
        
        if not name:
            return jsonify({'error': 'Category name is required'}), 400
        
        if len(name) > 100:
            return jsonify({'error': 'Category name must be 100 characters or less'}), 400
        
        user_id = get_current_user_id()
        
        # Check if category name already exists for this user
        check_sql = 'SELECT id FROM custom_categories WHERE user_id = %s AND name = %s'
        existing = run_query(check_sql, (user_id, name), fetch_one=True)
        if existing:
            return jsonify({'error': 'A category with this name already exists'}), 400
        
        # Create the custom category
        insert_sql = '''
            INSERT INTO custom_categories (user_id, name, icon, color, daily_budget)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        '''
        result = run_query(insert_sql, (user_id, name, icon, color, daily_budget), fetch_one=True)
        
        if result:
            category_id = result['id']
            
            # If daily_budget is set, also create a budget entry
            if daily_budget > 0:
                budget_sql = '''
                    INSERT INTO user_category_budgets (user_id, category_id, category_type, daily_budget)
                    VALUES (%s, %s, 'custom', %s)
                    ON CONFLICT (user_id, category_id, category_type) 
                    DO UPDATE SET daily_budget = EXCLUDED.daily_budget, updated_at = CURRENT_TIMESTAMP
                '''
                run_query(budget_sql, (user_id, category_id, daily_budget))
            
            return jsonify({
                'success': True,
                'category': {
                    'id': f'custom_{category_id}',
                    'name': name,
                    'icon': icon,
                    'color': color,
                    'daily_budget': float(daily_budget),
                    'is_default': False,
                    'is_custom': True
                }
            }), 201
        else:
            return jsonify({'error': 'Failed to create category'}), 500
            
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return jsonify({'error': 'Failed to create category'}), 500

@categories_bp.route('/categories/<int:category_id>/budget', methods=['PUT', 'POST'])
@require_auth
def update_category_budget(category_id):
    """Update daily budget for a specific category"""
    try:
        data = request.get_json()
        daily_budget = data.get('daily_budget')
        user_id = get_current_user_id()
        
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

@categories_bp.route('/categories/budgets', methods=['PUT', 'POST'])
@require_auth
def update_multiple_category_budgets():
    """Update daily budgets for multiple categories at once"""
    try:
        user_id = get_current_user_id()
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
                daily_budget = float(daily_budget)
                
                if daily_budget < 0:
                    errors.append(f"Category {category_id_str}: budget must be positive or zero")
                    continue
                
                # Parse category ID (format: "default_123" or "custom_456")
                if category_id_str.startswith('default_'):
                    category_type = 'default'
                    category_id = int(category_id_str.replace('default_', ''))
                    
                    # Check if default category exists
                    check_sql = 'SELECT id, name FROM default_categories WHERE id = %s'
                    category_exists = run_query(check_sql, (category_id,), fetch_one=True)
                    
                elif category_id_str.startswith('custom_'):
                    category_type = 'custom'
                    category_id = int(category_id_str.replace('custom_', ''))
                    
                    # Check if custom category exists and belongs to user
                    check_sql = 'SELECT id, name FROM custom_categories WHERE id = %s AND user_id = %s'
                    category_exists = run_query(check_sql, (category_id, user_id), fetch_one=True)
                    
                else:
                    # Legacy format - assume it's a default category
                    category_type = 'default'
                    category_id = int(category_id_str)
                    
                    check_sql = 'SELECT id, name FROM default_categories WHERE id = %s'
                    category_exists = run_query(check_sql, (category_id,), fetch_one=True)
                
                if not category_exists:
                    errors.append(f"Category {category_id_str}: not found")
                    continue
                
                # Update or insert budget in user_category_budgets table
                budget_sql = '''
                    INSERT INTO user_category_budgets (user_id, category_id, category_type, daily_budget)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, category_id, category_type) 
                    DO UPDATE SET daily_budget = EXCLUDED.daily_budget, updated_at = CURRENT_TIMESTAMP
                    RETURNING daily_budget
                '''
                result = run_query(budget_sql, (user_id, category_id, category_type, daily_budget), fetch_one=True)
                
                if result:
                    updated_categories.append({
                        'category_id': category_id_str,
                        'category_name': category_exists['name'],
                        'daily_budget': float(result['daily_budget'])
                    })
                else:
                    errors.append(f"Category {category_id_str}: failed to update budget")
                    
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

@categories_bp.route('/categories/budget-tracking', methods=['GET'])
@require_auth
def get_category_budget_tracking():
    """Get category budget tracking for today - spending vs. budget for each category"""
    try:
        day_offset = int(request.args.get('dayOffset', 0))
        user_id = get_current_user_id()
        today_start, today_end = get_day_bounds(day_offset, user_id)
        
        try:
            # Get all categories with their budgets for the current user (new normalized structure)
            categories_sql = '''
                SELECT 
                    'default_' || dc.id as id,
                    dc.name,
                    dc.icon,
                    dc.color,
                    COALESCE(ucb.daily_budget, 0.0) as daily_budget
                FROM default_categories dc
                LEFT JOIN user_category_budgets ucb ON ucb.category_id = dc.id 
                    AND ucb.category_type = 'default' 
                    AND ucb.user_id = %s
                
                UNION ALL
                
                SELECT 
                    'custom_' || cc.id as id,
                    cc.name,
                    cc.icon,
                    cc.color,
                    COALESCE(ucb.daily_budget, cc.daily_budget, 0.0) as daily_budget
                FROM custom_categories cc
                LEFT JOIN user_category_budgets ucb ON ucb.category_id = cc.id 
                    AND ucb.category_type = 'custom' 
                    AND ucb.user_id = %s
                WHERE cc.user_id = %s
                
                ORDER BY name ASC
            '''
            categories = run_query(categories_sql, (user_id, user_id, user_id), fetch_all=True)
            budgeted_count = sum(1 for cat in categories if cat['daily_budget'] > 0)
        except Exception as db_error:
            logger.error(f"Database error getting categories for budget tracking: {db_error}")
            # Return empty budget tracking if database fails
            return jsonify({
                'budgeted_categories': [],
                'unbedgeted_categories': [],
                'summary': {
                    'total_budget': 0,
                    'total_spent_budgeted': 0,
                    'total_spent_unbedgeted': 0,
                    'total_spent_all': 0,
                    'total_remaining': 0,
                    'overall_percentage_used': 0,
                    'budgeted_categories_count': 0,
                    'unbedgeted_categories_count': 0
                },
                'success': True
            })
        
        try:
            # Get today's spending by category (handle new category ID format)
            spending_sql = '''
                SELECT 
                    CASE 
                        WHEN e.category_id LIKE 'default_%%' THEN e.category_id
                        WHEN e.category_id LIKE 'custom_%%' THEN e.category_id
                        ELSE CONCAT('default_', e.category_id) -- Legacy format
                    END as category_id,
                    SUM(e.amount) as total_spent
                FROM expenses e
                WHERE e.user_id = %s AND e.timestamp >= %s AND e.timestamp < %s
                GROUP BY 
                    CASE 
                        WHEN e.category_id LIKE 'default_%%' THEN e.category_id
                        WHEN e.category_id LIKE 'custom_%%' THEN e.category_id
                        ELSE CONCAT('default_', e.category_id)
                    END
            '''
            spending_data = run_query(spending_sql, (user_id, today_start.isoformat(), today_end.isoformat()), fetch_all=True)
        except Exception as db_error:
            logger.error(f"Database error getting spending data: {db_error}")
            spending_data = []
        
        # Create spending lookup
        spending_by_category = {}
        for row in spending_data:
            category_id = row['category_id']
            spent = float(row['total_spent'])
            spending_by_category[category_id] = spent
        
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
        logger.error(f"Category budget tracking endpoint error: {e}")
        return jsonify({
            'budgeted_categories': [],
            'unbedgeted_categories': [],
            'summary': {
                'total_budget': 0,
                'total_spent_budgeted': 0,
                'total_spent_unbedgeted': 0,
                'total_spent_all': 0,
                'total_remaining': 0,
                'overall_percentage_used': 0,
                'budgeted_categories_count': 0,
                'unbedgeted_categories_count': 0
            },
            'success': True
        })

@categories_bp.route('/categories/<int:category_id>', methods=['DELETE'])
@require_auth
def delete_custom_category(category_id):
    """Delete a custom category for the current user"""
    try:
        user_id = get_current_user_id()
        
        # Check if category exists and belongs to user
        check_sql = '''
            SELECT id, name, user_id 
            FROM custom_categories 
            WHERE id = %s AND user_id = %s
        '''
        category = run_query(check_sql, (category_id, user_id), fetch_one=True)
        
        if not category:
            return jsonify({
                'error': 'Custom category not found or you do not have permission to delete it',
                'success': False
            }), 404
        
        # Check if category has any expenses
        expenses_sql = '''
            SELECT COUNT(*) as expense_count 
            FROM expenses 
            WHERE user_id = %s AND category_id = %s
        '''
        expenses_result = run_query(expenses_sql, (user_id, f'custom_{category_id}'), fetch_one=True)
        expense_count = expenses_result['expense_count'] if expenses_result else 0
        
        # Update expenses to remove category association (set to NULL)
        if expense_count > 0:
            update_expenses_sql = '''
                UPDATE expenses 
                SET category_id = NULL 
                WHERE user_id = %s AND category_id = %s
            '''
            run_query(update_expenses_sql, (user_id, f'custom_{category_id}'))
        
        # Delete category budgets
        delete_budgets_sql = '''
            DELETE FROM user_category_budgets 
            WHERE user_id = %s AND category_id = %s AND category_type = 'custom'
        '''
        run_query(delete_budgets_sql, (user_id, category_id))
        
        # Delete the custom category
        delete_category_sql = '''
            DELETE FROM custom_categories 
            WHERE id = %s AND user_id = %s
        '''
        result = run_query(delete_category_sql, (category_id, user_id), fetch_all=False)
        
        if result:
            return jsonify({
                'success': True,
                'message': f'Custom category "{category["name"]}" deleted successfully',
                'expenses_updated': expense_count
            })
        else:
            return jsonify({
                'error': 'Failed to delete custom category',
                'success': False
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting custom category: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500
