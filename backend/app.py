from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from flask_mail import Mail, Message
import sendgrid
from sendgrid.helpers.mail import Mail as SendGridMail
import psycopg2
import psycopg2.extras
import os
import bcrypt
import secrets
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from functools import wraps

# Load environment variables (for local development)
load_dotenv()

# Production fix - ensure proper session handling
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Enhanced session configuration for production
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Sessions last 7 days

# Set session cookie domain for custom domains (commented out for now)
# if os.environ.get('FLASK_ENV') == 'production':
#     # Allow session cookies to work with custom domains
#     app.config['SESSION_COOKIE_DOMAIN'] = None  # Let Flask auto-detect
CORS(app, supports_credentials=True)

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

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

# Authentication Helper Functions
def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def validate_email(email):
    """Validate email format using regex"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_reset_token():
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)

def send_password_reset_email_sendgrid(user_email, username, reset_token):
    """Send password reset email using SendGrid (Professional)"""
    try:
        # Get SendGrid API key from environment
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_api_key:
            print("SendGrid API key not configured, falling back to Gmail")
            return send_password_reset_email_gmail(user_email, username, reset_token)
        
        # Create the reset URL (dynamic for production)
        base_url = os.environ.get('BASE_URL', 'http://localhost:5001')
        reset_url = f"{base_url}/reset-password.html?token={reset_token}"
        
        # Create SendGrid client
        sg = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
        
        # Create HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9f9f9; }}
                .button {{ background: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }}
                .footer {{ color: #666; font-size: 12px; text-align: center; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌱 Sprout Budget Tracker</h1>
                </div>
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>Hello {username},</p>
                    <p>You requested a password reset for your Sprout Budget Tracker account.</p>
                    <p><a href="{reset_url}" class="button">Reset Your Password</a></p>
                    <p><strong>This link will expire in 1 hour</strong> for security reasons.</p>
                    <p>If you didn't request this password reset, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>Best regards,<br>The Sprout Team</p>
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create email message
        message = SendGridMail(
            from_email=os.environ.get('FROM_EMAIL', 'noreply@sproutbudget.com'),
            to_emails=user_email,
            subject="🌱 Reset Your Sprout Budget Password",
            html_content=html_content
        )
        
        # Send email
        response = sg.send(message)
        print(f"✅ SendGrid: Password reset email sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"❌ SendGrid failed: {e}")
        print("🔄 Falling back to Gmail...")
        return send_password_reset_email_gmail(user_email, username, reset_token)

def send_password_reset_email_gmail(user_email, username, reset_token):
    """Send password reset email using Gmail (Fallback)"""
    try:
        # Create the reset URL (dynamic for production)
        base_url = os.environ.get('BASE_URL', 'http://localhost:5001')
        reset_url = f"{base_url}/reset-password.html?token={reset_token}"
        
        # Create email message
        msg = Message(
            subject="Sprout Budget Tracker - Password Reset",
            recipients=[user_email],
            body=f"""Hello {username},

You requested a password reset for your Sprout Budget Tracker account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour for security reasons.

If you didn't request this password reset, please ignore this email.

Best regards,
The Sprout Team

--
This is an automated message. Please do not reply to this email."""
        )
        
        mail.send(msg)
        print(f"📧 Gmail: Password reset email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Gmail failed: {e}")
        return False

def send_password_reset_email(user_email, username, reset_token):
    """Send password reset email (tries SendGrid first, falls back to Gmail)"""
    print(f"📧 Starting email send process for {user_email}")
    print(f"🔧 Using username: {username}")
    print(f"🔑 Token: {reset_token[:10]}...")
    
    # Check environment variables
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    
    print(f"🔍 SendGrid API key: {'SET' if sendgrid_api_key else 'NOT SET'}")
    print(f"🔍 Gmail username: {'SET' if mail_username else 'NOT SET'}")
    print(f"🔍 Gmail password: {'SET' if mail_password else 'NOT SET'}")
    
    return send_password_reset_email_sendgrid(user_email, username, reset_token)

def require_auth(f):
    """Decorator to require authentication for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """Get the current user's ID from session"""
    return session.get('user_id')

def create_default_categories(user_id):
    """Create default categories for a new user"""
    # First check if user already has categories
    existing_count = run_query(
        'SELECT COUNT(*) as count FROM categories WHERE user_id = %s',
        (user_id,),
        fetch_one=True
    )
    
    if existing_count and existing_count['count'] > 0:
        print(f"User {user_id} already has {existing_count['count']} categories, skipping default creation")
        return
    
    print(f"Creating default categories for new user {user_id}")
    default_categories = [
        ('Food & Dining', '🍽️', '#FF6B6B'),
        ('Transportation', '🚗', '#4ECDC4'),
        ('Shopping', '🛒', '#45B7D1'),
        ('Health & Fitness', '💪', '#96CEB4'),
        ('Entertainment', '🎬', '#FECA57'),
        ('Bills & Utilities', '⚡', '#FF9FF3'),
        ('Other', '📝', '#6B7280')
    ]
    
    for name, icon, color in default_categories:
        # Check if this category already exists for this user
        existing = run_query(
            'SELECT id FROM categories WHERE user_id = %s AND name = %s',
            (user_id, name),
            fetch_one=True
        )
        
        if not existing:
            sql = '''
                INSERT INTO categories (user_id, name, icon, color, is_default)
                VALUES (%s, %s, %s, %s, TRUE)
            '''
            run_query(sql, (user_id, name, icon, color), fetch_all=False)
        else:
            print(f"Category '{name}' already exists for user {user_id}, skipping")
    
    # Create default user preferences (use ON CONFLICT to handle duplicates)
    sql = '''
        INSERT INTO user_preferences (user_id, daily_spending_limit)
        VALUES (%s, 30.00)
        ON CONFLICT (user_id) DO NOTHING
    '''
    run_query(sql, (user_id,), fetch_all=False)

# Helper: Get the start and end of the target day (using dayOffset)
def get_day_bounds(day_offset=0):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    target_day = today + timedelta(days=day_offset)
    start = target_day
    end = target_day + timedelta(days=1)
    return start, end

# Helper: Get all expenses between two datetimes with optional category filtering
def get_expenses_between(start, end, user_id, category_id=None):
    if category_id:
        # Filter by specific category
        sql = '''
            SELECT e.amount, e.description, e.timestamp, e.category_id,
                   c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.user_id = %s AND e.timestamp >= %s AND e.timestamp < %s AND e.category_id = %s
            ORDER BY e.timestamp DESC
        '''
        params = (user_id, start.isoformat(), end.isoformat(), category_id)
    else:
        # Get all expenses with category information
        sql = '''
            SELECT e.amount, e.description, e.timestamp, e.category_id,
                   c.name as category_name, c.icon as category_icon, c.color as category_color
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.user_id = %s AND e.timestamp >= %s AND e.timestamp < %s
            ORDER BY e.timestamp DESC
        '''
        params = (user_id, start.isoformat(), end.isoformat())
    
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

@app.route('/api/test-db')
def test_database():
    """Test database schema and connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if users table exists and get its schema
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]
        
        # Check if username column exists
        has_username = 'username' in column_names
        
        # Get user count
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'users_table_columns': column_names,
            'has_username_column': has_username,
            'user_count': user_count,
            'needs_migration': has_username,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'database': 'disconnected',
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 500

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
@require_auth
def get_expenses():
    # Get dayOffset from query string (?dayOffset=N), default to 0 (today)
    day_offset = int(request.args.get('dayOffset', 0))
    start, end = get_day_bounds(day_offset)
    
    user_id = get_current_user_id()
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

@app.route('/api/categories', methods=['GET'])
@require_auth
def get_categories():
    """Get all categories for the current user (default + custom)"""
    try:
        user_id = get_current_user_id()
        
        try:
            # Get default categories (shared by all users)
            default_sql = '''
                SELECT id, name, icon, color, created_at
                FROM default_categories 
                ORDER BY name ASC
            '''
            default_categories = run_query(default_sql, fetch_all=True)
            
            # Get custom categories for this user
            custom_sql = '''
                SELECT id, name, icon, color, daily_budget, created_at
                FROM custom_categories 
                WHERE user_id = %s
                ORDER BY name ASC
            '''
            custom_categories = run_query(custom_sql, (user_id,), fetch_all=True)
            
            # Get user's budget settings for all categories
            budget_sql = '''
                SELECT category_id, category_type, daily_budget
                FROM user_category_budgets 
                WHERE user_id = %s
            '''
            user_budgets = run_query(budget_sql, (user_id,), fetch_all=True)
            
            # Create a lookup for user budgets
            budget_lookup = {}
            for budget in user_budgets:
                key = f"{budget['category_type']}_{budget['category_id']}"
                budget_lookup[key] = float(budget['daily_budget'])
            
            # Combine and format categories
            categories = []
            
            # Add default categories
            for cat in default_categories:
                budget_key = f"default_{cat['id']}"
                categories.append({
                    'id': f"default_{cat['id']}",  # Prefix to distinguish from custom
                    'name': cat['name'],
                    'icon': cat['icon'],
                    'color': cat['color'],
                    'daily_budget': budget_lookup.get(budget_key, 0.0),
                    'is_default': True,
                    'is_custom': False,
                    'created_at': cat['created_at'].isoformat() if hasattr(cat['created_at'], 'isoformat') else str(cat['created_at'])
                })
            
            # Add custom categories
            for cat in custom_categories:
                budget_key = f"custom_{cat['id']}"
                categories.append({
                    'id': f"custom_{cat['id']}",  # Prefix to distinguish from default
                    'name': cat['name'],
                    'icon': cat['icon'],
                    'color': cat['color'],
                    'daily_budget': budget_lookup.get(budget_key, float(cat['daily_budget'])),
                    'is_default': False,
                    'is_custom': True,
                    'created_at': cat['created_at'].isoformat() if hasattr(cat['created_at'], 'isoformat') else str(cat['created_at'])
                })
            
            return jsonify(categories)
            
        except Exception as db_error:
            print(f"Database error getting categories: {db_error}")
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
        print(f"Error in get_categories: {e}")
        return jsonify({'error': 'Failed to load categories'}), 500

@app.route('/api/categories', methods=['POST'])
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
        print(f"Error creating category: {e}")
        return jsonify({'error': 'Failed to create category'}), 500

@app.route('/api/categories/<int:category_id>/budget', methods=['PUT', 'POST'])
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

@app.route('/api/categories/budgets', methods=['PUT', 'POST'])
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

@app.route('/api/categories/budget-tracking', methods=['GET'])
@require_auth
def get_category_budget_tracking():
    """Get category budget tracking for today - spending vs. budget for each category"""
    try:
        day_offset = int(request.args.get('dayOffset', 0))
        today_start, today_end = get_day_bounds(day_offset)
        user_id = get_current_user_id()
        
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
        except Exception as db_error:
            print(f"Database error getting categories for budget tracking: {db_error}")
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
            spending_data = run_query(spending_sql, (user_id, today_start.isoformat(), today_end.isoformat()))
        except Exception as db_error:
            print(f"Database error getting spending data: {db_error}")
            spending_data = []
        
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
        print(f"Category budget tracking endpoint error: {e}")
        import traceback
        traceback.print_exc()
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

@app.route('/api/expenses', methods=['POST'])
@require_auth
def add_expense():
    try:
        print(f"🔍 Add expense request received")
        data = request.get_json()
        if not data:
            print(f"❌ No data provided in request")
            return jsonify({'error': 'No data provided'}), 400
            
        amount = data.get('amount')
        description = data.get('description', '')
        category_id = data.get('category_id')  # New: category selection
        
        print(f"📊 Request data: amount={amount}, description='{description}', category_id={category_id}")
        
        if amount is None:
            print(f"❌ Amount is missing")
            return jsonify({'error': 'Amount is required'}), 400
        
        user_id = get_current_user_id()
        print(f"👤 User ID: {user_id}")
        
        # Check user's category requirement preference
        try:
            sql = 'SELECT require_categories FROM user_preferences WHERE user_id = %s'
            result = run_query(sql, (user_id,), fetch_one=True)
            require_categories = result['require_categories'] if result else True  # Default to True
            print(f"🔍 User category preference: require_categories={require_categories}")
        except Exception as e:
            print(f"⚠️ Error checking category preference, defaulting to required: {e}")
            require_categories = True
        
        # Validate category_id based on user preference
        if require_categories and not category_id:
            print(f"❌ Category ID is missing and categories are required")
            return jsonify({'error': 'Category is required'}), 400
        elif not require_categories and not category_id:
            print(f"ℹ️ Category ID is missing but categories are optional, proceeding without category")
            category_id = None
        print(f"👤 User ID: {user_id}")
        
        # Validate category_id if provided
        if category_id:
            try:
                # Parse category ID (format: "default_123" or "custom_456")
                if isinstance(category_id, str) and '_' in category_id:
                    category_type, cat_id = category_id.split('_', 1)
                    category_id = int(cat_id)
                else:
                    # Legacy format - assume it's a custom category
                    category_id = int(category_id)
                    category_type = 'custom'
                
                print(f"🔍 Checking if {category_type} category {category_id} exists for user {user_id}")
                
                if category_type == 'default':
                    # Check if default category exists
                    check_sql = 'SELECT id FROM default_categories WHERE id = %s'
                    category_exists = run_query(check_sql, (category_id,), fetch_one=True)
                else:
                    # Check if custom category exists and belongs to the user
                    check_sql = 'SELECT id FROM custom_categories WHERE id = %s AND user_id = %s'
                    category_exists = run_query(check_sql, (category_id, user_id), fetch_one=True)
                
                if not category_exists:
                    print(f"❌ {category_type} category {category_id} not found for user {user_id}")
                    return jsonify({'error': 'Invalid category'}), 400
                print(f"✅ {category_type} category {category_id} validated")
                
            except (ValueError, TypeError) as e:
                print(f"❌ Invalid category ID format: {e}")
                return jsonify({'error': 'Invalid category ID'}), 400
            except Exception as db_error:
                print(f"❌ Database error checking category: {db_error}")
                import traceback
                traceback.print_exc()
                return jsonify({'error': 'Database connection error. Please try again.'}), 503
        else:
            print(f"ℹ️ No category provided, expense will be saved without category")
        
        # Use UTC timestamp to ensure consistent date handling across timezones
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        print(f"⏰ Timestamp: {timestamp}")
        
        try:
            print(f"💾 Inserting expense into database...")
            sql = '''
                INSERT INTO expenses (user_id, amount, description, category_id, timestamp)
                VALUES (%s, %s, %s, %s, %s)
            '''
            result = run_query(sql, (user_id, amount, description, category_id, timestamp), fetch_all=False)
            print(f"✅ Expense inserted successfully, result: {result}")
            return jsonify({'success': True}), 201
        except Exception as db_error:
            print(f"❌ Database error adding expense: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Failed to save expense. Please try again.'}), 503
            
    except Exception as e:
        print(f"❌ Add expense endpoint error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred. Please try again.'}), 500

@app.route('/api/summary', methods=['GET'])
@require_auth
def get_summary():
    try:
        day_offset = int(request.args.get('dayOffset', 0))
        today_start, today_end = get_day_bounds(day_offset)
        
        user_id = get_current_user_id()
        
        # Get user's daily limit with fallback
        try:
            user_daily_limit = get_user_daily_limit(user_id)
        except Exception as e:
            print(f"Error getting user daily limit: {e}, using default")
            user_daily_limit = 30.0
        
        # Calculate daily surplus for the last 7 days
        deltas = []
        for i in range(7):
            offset = day_offset - i
            day_start, day_end = get_day_bounds(offset)
            try:
                expenses = get_expenses_between(day_start, day_end, user_id)
                total_spent = sum(e['amount'] for e in expenses)
                daily_surplus = user_daily_limit - total_spent
                deltas.append(daily_surplus)
            except Exception as e:
                print(f"Error calculating day {i}: {e}, using default")
                deltas.append(user_daily_limit)  # Assume no spending
        
        # Today's balance and averages
        today_balance = deltas[0] if deltas else user_daily_limit
        avg_daily_surplus = sum(deltas) / 7 if deltas else user_daily_limit  # Always divide by 7 days
        projection_30 = avg_daily_surplus * 30  # 30-day projection based on average daily surplus
        
        # Plant state logic - prioritize today's spending over 7-day average
        print(f"DEBUG: today_balance={today_balance}, avg_daily_surplus={avg_daily_surplus}")
        
        if today_balance < 0:
            # Today's spending exceeded the daily limit
            if today_balance >= -5:
                plant = 'wilting'
                plant_emoji = '🥀'
                print(f"DEBUG: Plant set to wilting (today_balance={today_balance})")
            else:
                plant = 'dead'
                plant_emoji = '☠️'
                print(f"DEBUG: Plant set to dead (today_balance={today_balance})")
        elif today_balance >= 10 and avg_daily_surplus >= 2:
            plant = 'thriving'
            plant_emoji = '🌳'
            print(f"DEBUG: Plant set to thriving")
        elif today_balance >= 0 and avg_daily_surplus >= -2:
            plant = 'healthy'
            plant_emoji = '🌱'
            print(f"DEBUG: Plant set to healthy")
        else:
            plant = 'struggling'
            plant_emoji = '🌿'
            print(f"DEBUG: Plant set to struggling")
        
        print(f"DEBUG: Final plant state={plant}, emoji={plant_emoji}")
        
        return jsonify({
            'balance': round(today_balance, 2),
            'avg_7day': round(avg_daily_surplus, 2),
            'projection_30': round(projection_30, 2),
            'plant_state': plant,
            'plant_emoji': plant_emoji
        })
        
    except Exception as e:
        print(f"Summary endpoint error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return a safe fallback response instead of crashing
        return jsonify({
            'balance': 30.0,
            'avg_7day': 30.0,
            'projection_30': 900.0,
            'plant_state': 'healthy',
            'plant_emoji': '🌱'
        })

@app.route('/api/history', methods=['GET'])
@require_auth
def get_history():
    try:
        # Get all expenses from the last 7 days (including today)
        day_offset = int(request.args.get('dayOffset', 0))
        period = int(request.args.get('period', 7))  # Default to 7 days
        category_id = request.args.get('category_id')  # Optional category filter
        
        user_id = get_current_user_id()
        start_date, _ = get_day_bounds(day_offset - (period - 1))
        _, end_date = get_day_bounds(day_offset)
        
        try:
            expenses = get_expenses_between(start_date, end_date, user_id, category_id)
        except Exception as e:
            print(f"Error getting expenses: {e}")
            # Return empty history instead of crashing
            return jsonify([])
        
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
        
    except Exception as e:
        print(f"History endpoint error: {e}")
        import traceback
        traceback.print_exc()
        # Return empty history instead of crashing
        return jsonify([])

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

@app.route('/api/preferences/daily-limit', methods=['POST', 'PUT'])
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

@app.route('/api/preferences/category-requirement', methods=['GET'])
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

@app.route('/api/preferences/category-requirement', methods=['POST', 'PUT'])
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

# Authentication Routes
@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """User registration with email-only authentication"""
    try:
        # Enhanced request parsing with better error handling
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        print(f"Signup attempt - Email: {email}")
        
        # Enhanced validation with specific error messages
        if not email or not password:
            missing_fields = []
            if not email: missing_fields.append('email')
            if not password: missing_fields.append('password')
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Please enter a valid email address'}), 400
        
        # Check if email already exists with better error handling
        try:
            existing_email = run_query(
                'SELECT id FROM users WHERE email = %s',
                (email,),
                fetch_one=True
            )
            if existing_email:
                print(f"Signup failed - Email already exists: {email}")
                return jsonify({'error': 'An account with this email already exists. Please use a different email or try logging in.'}), 409
        except Exception as db_error:
            print(f"Database error checking email: {db_error}")
            return jsonify({'error': 'Database connection error. Please try again.'}), 503
        
        # Hash password and create user with enhanced error handling
        try:
            password_hash = hash_password(password)
            sql = '''
                INSERT INTO users (email, password_hash)
                VALUES (%s, %s)
                RETURNING id, email
            '''
            result = run_query(sql, (email, password_hash), fetch_one=True)
            
            if not result:
                print(f"Failed to create user account for {email}")
                return jsonify({'error': 'Failed to create account. Please try again.'}), 500
                
            user_id = result['id']
            print(f"User created successfully - ID: {user_id}, Email: {email}")
            
            # Create default categories and preferences for new user
            try:
                create_default_categories(user_id)
                print(f"Default categories created for user {user_id}")
            except Exception as cat_error:
                # If categories creation fails, delete the user to maintain consistency
                print(f"Failed to create default categories for user {user_id}: {cat_error}")
                try:
                    delete_sql = 'DELETE FROM users WHERE id = %s'
                    run_query(delete_sql, (user_id,), fetch_all=False)
                    print(f"Rolled back user creation for {user_id}")
                except Exception as delete_error:
                    print(f"Failed to rollback user creation: {delete_error}")
                return jsonify({'error': 'Failed to set up account. Please try again.'}), 500
            
            # Automatically log the user in after successful signup
            session.clear()  # Clear any existing session
            session['user_id'] = user_id
            session.permanent = True  # Make session persistent
            
            print(f"User {user_id} automatically logged in after signup")
            
            return jsonify({
                'message': 'Account created successfully! You are now logged in.',
                'user': {
                    'id': result['id'],
                    'email': result['email']
                },
                'auto_login': True
            }), 201
            
        except Exception as create_error:
            print(f"Error creating user account: {create_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Failed to create account. Please try again.'}), 500
            
    except Exception as e:
        print(f"Unexpected signup error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login with email and password"""
    try:
        # Enhanced request parsing with better error handling
        if not request.is_json:
            return jsonify({'error': 'Request must be JSON'}), 400
            
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No login data provided'}), 400
            
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        print(f"Login attempt for: {email}")
        
        if not email or not password:
            missing_fields = []
            if not email: missing_fields.append('email')
            if not password: missing_fields.append('password')
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Please enter a valid email address'}), 400
        
        # Login with email
        try:
            sql = 'SELECT id, email, password_hash FROM users WHERE email = %s'
            print(f"Attempting email login for: {email}")
            
            user = run_query(sql, (email,), fetch_one=True)
            
            if not user:
                print(f"No user found for: {email}")
                return jsonify({'error': 'Invalid email or password'}), 401
                
            print(f"User found - ID: {user['id']}, Email: {user['email']}")
            
            # Verify password
            if not verify_password(password, user['password_hash']):
                print(f"Invalid password for user: {email}")
                return jsonify({'error': 'Invalid email or password'}), 401
            
            # Set session with enhanced session management
            session.clear()  # Clear any existing session data
            session['user_id'] = user['id']
            session['email'] = user['email']
            session.permanent = True  # Make session permanent
            
            print(f"Login successful for user {user['id']} ({user['email']})")
            
            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': user['id'],
                    'email': user['email']
                }
            }), 200
            
        except Exception as db_error:
            print(f"Database error during login: {db_error}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': 'Database connection error. Please try again.'}), 503
        
    except Exception as e:
        print(f"Unexpected login error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'An unexpected error occurred. Please try again later.'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """User logout"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@app.route('/api/auth/me', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user information"""
    try:
        sql = 'SELECT id, email, created_at FROM users WHERE id = %s'
        user = run_query(sql, (session['user_id'],), fetch_one=True)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': {
                'id': user['id'],
                'email': user['email'],
                'created_at': user['created_at'].isoformat() if user['created_at'] else None
            }
        }), 200
        
    except Exception as e:
        print(f"Get current user error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# @app.route('/api/auth/debug-session', methods=['GET'])
# def debug_session():
#     """Debug endpoint to check session status"""
#     try:
#         session_data = {
#             'has_session': 'user_id' in session,
#             'user_id': session.get('user_id'),
#             'email': session.get('email'),
#             'session_keys': list(session.keys()),
#             'request_headers': dict(request.headers),
#             'cookies': dict(request.cookies),
#             'flask_env': os.environ.get('FLASK_ENV'),
#             'session_secure': app.config.get('SESSION_COOKIE_SECURE'),
#             'session_httponly': app.config.get('SESSION_COOKIE_HTTPONLY'),
#             'session_samesite': app.config.get('SESSION_COOKIE_SAMESITE'),
#             'session_domain': app.config.get('SESSION_COOKIE_DOMAIN')
#         }
#         
#         return jsonify(session_data), 200
#         
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Initiate password reset process"""
    try:
        print("🔍 Forgot password request received")
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        print(f"📧 Email provided: {email}")
        
        if not email:
            print("❌ No email provided")
            return jsonify({'error': 'Email address is required'}), 400
        
        if not validate_email(email):
            print("❌ Invalid email format")
            return jsonify({'error': 'Please enter a valid email address'}), 400
        
        print("✅ Email validation passed")
        
        # Check if user exists
        user = run_query(
            'SELECT id, email FROM users WHERE email = %s',
            (email,),
            fetch_one=True
        )
        
        if user:
            print(f"✅ User found: ID {user['id']}, Email {user['email']}")
            
            # Generate reset token
            reset_token = generate_reset_token()
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # Token expires in 1 hour
            
            print(f"🔑 Generated reset token: {reset_token[:10]}...")
            
            # Store token in database
            sql = '''
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (%s, %s, %s)
            '''
            run_query(sql, (user['id'], reset_token, expires_at), fetch_all=False)
            print("💾 Token stored in database")
            
            # Send email (use email as display name since no username)
            print("📧 Attempting to send password reset email...")
            email_sent = send_password_reset_email(user['email'], user['email'], reset_token)
            
            if email_sent:
                print(f"✅ Password reset email sent successfully to {user['email']}")
            else:
                print(f"❌ Failed to send password reset email to {user['email']}")
        else:
            print(f"⚠️ No user found with email: {email}")
        
        # Always return the same message for security
        return jsonify({
            'message': 'If an account with that email exists, we\'ve sent password reset instructions.'
        }), 200
        
    except Exception as e:
        print(f"❌ Forgot password error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    try:
        data = request.get_json()
        token = data.get('token', '').strip()
        new_password = data.get('password', '')
        
        if not token or not new_password:
            return jsonify({'error': 'Token and new password are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Find valid token
        sql = '''
            SELECT prt.user_id, prt.id as token_id, u.email
            FROM password_reset_tokens prt
            JOIN users u ON prt.user_id = u.id
            WHERE prt.token = %s 
            AND prt.expires_at > NOW() 
            AND prt.used = FALSE
        '''
        token_data = run_query(sql, (token,), fetch_one=True)
        
        if not token_data:
            return jsonify({'error': 'Invalid or expired reset token'}), 400
        
        # Hash new password
        password_hash = hash_password(new_password)
        
        # Update user password
        run_query(
            'UPDATE users SET password_hash = %s WHERE id = %s',
            (password_hash, token_data['user_id']),
            fetch_all=False
        )
        
        # Mark token as used
        run_query(
            'UPDATE password_reset_tokens SET used = TRUE WHERE id = %s',
            (token_data['token_id'],),
            fetch_all=False
        )
        
        print(f"Password reset completed for user {token_data['user_id']} ({token_data['email']})")
        
        return jsonify({'message': 'Password reset successful! You can now log in with your new password.'}), 200
        
    except Exception as e:
        print(f"Reset password error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Get the frontend directory path relative to this file
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')

@app.route('/')
def serve_index():
    response = send_from_directory(FRONTEND_DIR, 'index.html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/auth.html')
def serve_auth():
    response = send_from_directory(FRONTEND_DIR, 'auth.html')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/reset-password.html')
def serve_reset_password():
    return send_from_directory(FRONTEND_DIR, 'reset-password.html')

# @app.route('/debug-session.html')
# def serve_debug_session():
#     return send_from_directory(FRONTEND_DIR, 'debug-session.html')

@app.route('/history.html')
def serve_history():
    return send_from_directory(FRONTEND_DIR, 'history.html')

@app.route('/settings.html')
def serve_settings():
    return send_from_directory(FRONTEND_DIR, 'settings.html')

@app.route('/debug-api.html')
def serve_debug_api():
    return send_from_directory(FRONTEND_DIR, 'debug-api.html')

@app.route('/api/debug/email-config')
def debug_email_config():
    """Debug endpoint to check email configuration"""
    try:
        # Check Gmail configuration
        mail_server = os.environ.get('MAIL_SERVER')
        mail_port = os.environ.get('MAIL_PORT')
        mail_username = os.environ.get('MAIL_USERNAME')
        mail_password = os.environ.get('MAIL_PASSWORD')
        mail_default_sender = os.environ.get('MAIL_DEFAULT_SENDER')
        
        # Check SendGrid configuration
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        from_email = os.environ.get('FROM_EMAIL')
        
        # Check app configuration
        base_url = os.environ.get('BASE_URL')
        flask_env = os.environ.get('FLASK_ENV')
        
        config = {
            'gmail': {
                'server': mail_server,
                'port': mail_port,
                'username': mail_username,
                'password_set': bool(mail_password),
                'default_sender': mail_default_sender,
                'configured': all([mail_server, mail_username, mail_password])
            },
            'sendgrid': {
                'api_key_set': bool(sendgrid_api_key),
                'from_email': from_email,
                'configured': bool(sendgrid_api_key)
            },
            'app': {
                'base_url': base_url,
                'flask_env': flask_env
            },
            'summary': {
                'gmail_configured': all([mail_server, mail_username, mail_password]),
                'sendgrid_configured': bool(sendgrid_api_key),
                'email_should_work': all([mail_server, mail_username, mail_password]) or bool(sendgrid_api_key)
            }
        }
        
        return jsonify(config)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/<path:filename>')
def serve_static(filename):
    response = send_from_directory(FRONTEND_DIR, filename)
    
    # Add cache control for CSS and JS files
    if filename.endswith(('.css', '.js')):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    
    return response

if __name__ == '__main__':
    # Only run the development server if this file is run directly
    # In production, gunicorn will import and run the app
    app.run(debug=DEBUG, port=PORT, host='0.0.0.0') 