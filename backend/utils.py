import os
import bcrypt
import secrets
import re
import logging
import logging.handlers
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
from functools import wraps

# Load environment variables
load_dotenv()

# ==========================================
# LOGGING CONFIGURATION
# ==========================================

def setup_logging():
    """Configure structured logging for the application"""
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Determine log level from environment
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create handlers
    handlers = []
    
    # Console handler (always active)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler for all logs
    file_handler = logging.handlers.RotatingFileHandler(
        'logs/app.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(formatter)
    handlers.append(file_handler)
    
    # Error file handler (errors only)
    error_handler = logging.handlers.RotatingFileHandler(
        'logs/errors.log',
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)
    handlers.append(error_handler)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add our handlers
    for handler in handlers:
        root_logger.addHandler(handler)
    
    # Create app logger
    app_logger = logging.getLogger('sprout_app')
    app_logger.info(f"Logging initialized at level: {log_level}")
    
    return app_logger

# Initialize logging
logger = setup_logging()

# ==========================================
# CACHING CONFIGURATION
# ==========================================

# Simple in-memory cache for frequently accessed data
_cache = {}
_cache_timestamps = {}

def get_cached_data(key, max_age_seconds=300):  # 5 minutes default
    """Get data from cache if it's still valid"""
    if key in _cache and key in _cache_timestamps:
        age = time.time() - _cache_timestamps[key]
        if age < max_age_seconds:
            return _cache[key]
        else:
            # Cache expired, remove it
            del _cache[key]
            del _cache_timestamps[key]
    return None

def set_cached_data(key, data, max_age_seconds=300):
    """Store data in cache with timestamp"""
    _cache[key] = data
    _cache_timestamps[key] = time.time()

def clear_cache():
    """Clear all cached data"""
    _cache.clear()
    _cache_timestamps.clear()

def log_with_context(level, message, **context):
    """Helper function for structured logging with context"""
    from flask import request
    
    extra_data = {
        'user_id': getattr(request, 'user_id', None) if hasattr(request, 'user_id') else None,
        'ip_address': request.remote_addr if hasattr(request, 'remote_addr') else None,
        'user_agent': request.headers.get('User-Agent') if hasattr(request, 'headers') else None,
        'endpoint': request.endpoint if hasattr(request, 'endpoint') else None,
        'method': request.method if hasattr(request, 'method') else None,
        **context
    }
    
    # Filter out None values
    extra_data = {k: v for k, v in extra_data.items() if v is not None}
    
    if level == 'debug':
        logger.debug(message, extra=extra_data)
    elif level == 'info':
        logger.info(message, extra=extra_data)
    elif level == 'warning':
        logger.warning(message, extra=extra_data)
    elif level == 'error':
        logger.error(message, extra=extra_data)
    elif level == 'critical':
        logger.critical(message, extra=extra_data)

# ==========================================
# CUSTOM EXCEPTIONS FOR ROBUST ERROR HANDLING
# ==========================================

class SproutError(Exception):
    """Base exception for Sprout application"""
    def __init__(self, message, code=None, status_code=500, field=None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.field = field
        super().__init__(self.message)

class ValidationError(SproutError):
    """Raised when input validation fails"""
    def __init__(self, message, field=None):
        super().__init__(message, code='VALIDATION_ERROR', status_code=400, field=field)

class AuthenticationError(SproutError):
    """Raised when authentication fails"""
    def __init__(self, message):
        super().__init__(message, code='AUTHENTICATION_ERROR', status_code=401)

class DatabaseError(SproutError):
    """Raised when database operations fail"""
    def __init__(self, message):
        super().__init__(message, code='DATABASE_ERROR', status_code=503)

class NotFoundError(SproutError):
    """Raised when a resource is not found"""
    def __init__(self, message, resource_type=None):
        super().__init__(message, code='NOT_FOUND', status_code=404)
        self.resource_type = resource_type

# Legacy exception for backward compatibility
class DatabaseConnectionError(Exception):
    pass

# ==========================================
# ULTRA-CONSERVATIVE SECURITY
# ==========================================

def log_security_event(event_type, details=None):
    """Log security events for monitoring - passive only"""
    from flask import request
    
    logger.info(f"Security event: {event_type}", extra={
        'security_event': event_type,
        'ip_address': request.remote_addr if hasattr(request, 'remote_addr') else None,
        'user_agent': request.headers.get('User-Agent') if hasattr(request, 'headers') else None,
        'details': details
    })

def sanitize_input_passive(text):
    """Passive input sanitization - only removes obvious malicious content"""
    if not text or not isinstance(text, str):
        return text
    
    # Only remove obvious malicious patterns
    malicious_patterns = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'data:text/html',  # Data URLs
        r'vbscript:',  # VBScript protocol
    ]
    
    sanitized = text
    for pattern in malicious_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
    
    return sanitized

def add_security_headers_passive(response):
    """Add basic security headers - passive only"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response

# ==========================================
# DATABASE CONFIGURATION
# ==========================================

# Configuration from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")
BUDGET = float(os.environ.get("DAILY_BUDGET", "30.0"))  # Daily budget amount
PORT = int(os.environ.get("PORT", "5001"))  # Server port
DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"  # Debug mode

def get_db_connection():
    """Get a database connection with dict cursor for easy column access"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        logger.debug("Database connection established successfully")
        return conn
    except Exception as e:
        logger.error("Failed to establish database connection", exc_info=True, extra={
            'database_url': DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'unknown'
        })
        raise DatabaseConnectionError(f"Database connection failed: {e}")

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
            
            if sql.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP')):
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
        logger.error("Database query failed", exc_info=True, extra={
            'sql': sql[:100] + '...' if len(sql) > 100 else sql,
            'params': str(params)[:100] if params else None,
            'error_code': e.pgcode,
            'error_message': str(e)
        })
        raise DatabaseConnectionError(f"Database unavailable: {e}")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error("Unexpected error in database query", exc_info=True, extra={
            'sql': sql[:100] + '...' if len(sql) > 100 else sql,
            'params': str(params)[:100] if params else None
        })
        raise e
    finally:
        if conn:
            conn.close()

# ==========================================
# AUTHENTICATION HELPER FUNCTIONS
# ==========================================

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

# ==========================================
# VALIDATION FUNCTIONS
# ==========================================

def validate_expense_data(data):
    """Validate expense input data"""
    if not data:
        raise ValidationError("No data provided", field="data")
    
    amount = data.get('amount')
    if amount is None:
        raise ValidationError("Amount is required", field="amount")
    
    try:
        amount = float(amount)
        if amount <= 0:
            raise ValidationError("Amount must be greater than 0", field="amount")
    except (ValueError, TypeError):
        raise ValidationError("Amount must be a valid number", field="amount")
    
    description = data.get('description', '').strip()
    if len(description) > 500:
        raise ValidationError("Description too long (max 500 characters)", field="description")
    
    # Passive input sanitization - only removes obvious malicious content
    description = sanitize_input_passive(description)
    
    return {
        'amount': amount,
        'description': description
    }

def validate_auth_data(data):
    """Validate authentication input data"""
    if not data:
        raise ValidationError("No data provided", field="data")
    
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    
    if not email:
        raise ValidationError("Email is required", field="email")
    
    if not password:
        raise ValidationError("Password is required", field="password")
    
    if not validate_email(email):
        raise ValidationError("Please enter a valid email address", field="email")
    
    if len(password) < 6:
        raise ValidationError("Password must be at least 6 characters", field="password")
    
    return {
        'email': email,
        'password': password
    }

def validate_category_data(data):
    """Validate category input data"""
    if not data:
        raise ValidationError("No data provided", field="data")
    
    name = data.get('name', '').strip()
    if not name:
        raise ValidationError("Category name is required", field="name")
    
    if len(name) > 100:
        raise ValidationError("Category name too long (max 100 characters)", field="name")
    
    daily_budget = data.get('daily_budget', 0.0)
    try:
        daily_budget = float(daily_budget)
        if daily_budget < 0:
            raise ValidationError("Daily budget cannot be negative", field="daily_budget")
    except (ValueError, TypeError):
        raise ValidationError("Daily budget must be a valid number", field="daily_budget")
    
    return {
        'name': name,
        'daily_budget': daily_budget
    }

# ==========================================
# ERROR HANDLER DECORATOR
# ==========================================

def handle_errors(f):
    """Decorator to handle errors consistently across endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except SproutError as e:
            logger.warning(f"Application error: {e.message}", extra={
                'error_code': e.code,
                'status_code': e.status_code,
                'field': e.field
            })
            return jsonify({
                'error': e.message,
                'code': e.code,
                'field': e.field
            }), e.status_code
        except psycopg2.OperationalError as e:
            logger.error("Database connection error", exc_info=True)
            return jsonify({
                'error': 'Database temporarily unavailable. Please try again.',
                'code': 'DATABASE_UNAVAILABLE'
            }), 503
        except psycopg2.IntegrityError as e:
            logger.warning("Data integrity violation", extra={
                'constraint': getattr(e.diag, 'constraint_name', 'unknown')
            })
            return jsonify({
                'error': 'Invalid data provided. Please check your input.',
                'code': 'DATA_INTEGRITY_ERROR'
            }), 400
        except ValueError as e:
            logger.warning("Invalid input data", extra={'error': str(e)})
            return jsonify({
                'error': 'Please provide valid data.',
                'code': 'INVALID_INPUT'
            }), 400
        except Exception as e:
            logger.error("Unexpected error", exc_info=True)
            return jsonify({
                'error': 'An unexpected error occurred. Please try again.',
                'code': 'INTERNAL_ERROR'
            }), 500
    return decorated_function

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_day_bounds(day_offset=0):
    """Get the start and end of the target day (using dayOffset)"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    target_day = today + timedelta(days=day_offset)
    start = target_day
    end = target_day + timedelta(days=1)
    return start, end

def get_expenses_between(start, end, user_id, category_id=None):
    """Get all expenses between two datetimes with optional category filtering"""
    if category_id:
        # Filter by specific category
        sql = '''
            SELECT e.id, e.amount, e.description, e.timestamp, e.category_id,
                   COALESCE(dc.name, cc.name) as category_name,
                   COALESCE(dc.icon, cc.icon) as category_icon,
                   COALESCE(dc.color, cc.color) as category_color
            FROM expenses e
            LEFT JOIN default_categories dc ON e.category_id = CONCAT('default_', dc.id::text)
            LEFT JOIN custom_categories cc ON e.category_id = CONCAT('custom_', cc.id::text) AND cc.user_id = e.user_id
            WHERE e.user_id = %s AND e.timestamp >= %s AND e.timestamp < %s AND e.category_id = %s
            ORDER BY e.timestamp DESC
        '''
        params = (user_id, start.isoformat(), end.isoformat(), category_id)
    else:
        # Get all expenses with category information
        sql = '''
            SELECT e.id, e.amount, e.description, e.timestamp, e.category_id,
                   COALESCE(dc.name, cc.name) as category_name,
                   COALESCE(dc.icon, cc.icon) as category_icon,
                   COALESCE(dc.color, cc.color) as category_color
            FROM expenses e
            LEFT JOIN default_categories dc ON e.category_id = CONCAT('default_', dc.id::text)
            LEFT JOIN custom_categories cc ON e.category_id = CONCAT('custom_', cc.id::text) AND cc.user_id = e.user_id
            WHERE e.user_id = %s AND e.timestamp >= %s AND e.timestamp < %s
            ORDER BY e.timestamp DESC
        '''
        params = (user_id, start.isoformat(), end.isoformat())
    
    raw_expenses = run_query(sql, params)
    
    # Convert data types for consistency
    expenses = []
    for e in raw_expenses:
        expense_data = {
            'id': e['id'],  # Include the expense ID
            'amount': float(e['amount']),
            'description': e['description'],
            'timestamp': e['timestamp'].isoformat() if hasattr(e['timestamp'], 'isoformat') else str(e['timestamp'])
        }
        
        # Add category information if present
        if e['category_id'] and e['category_name']:
            # Determine if this is a default or custom category
            if e['category_id'].startswith('default_'):
                is_default = True
                numeric_id = e['category_id'].replace('default_', '')
            elif e['category_id'].startswith('custom_'):
                is_default = False
                numeric_id = e['category_id'].replace('custom_', '')
            else:
                # Legacy format, assume custom
                is_default = False
                numeric_id = e['category_id']
            
            expense_data['category'] = {
                'id': numeric_id,
                'name': e['category_name'],
                'icon': e['category_icon'],
                'color': e['category_color'],
                'is_default': is_default
            }
        else:
            expense_data['category'] = None
            
        expenses.append(expense_data)
    
    return expenses

def get_user_daily_limit(user_id=0):
    """Get the user's daily spending limit from preferences with caching"""
    cache_key = f"daily_limit_{user_id}"
    
    # Check cache first
    cached_value = get_cached_data(cache_key, max_age_seconds=600)  # 10 minutes
    if cached_value is not None:
        return cached_value
    
    try:
        sql = 'SELECT daily_spending_limit FROM user_preferences WHERE user_id = %s'
        result = run_query(sql, (user_id,), fetch_one=True)
        if result:
            daily_limit = float(result['daily_spending_limit'])
        else:
            # If no preference found, create default and return it
            sql = '''
                INSERT INTO user_preferences (user_id, daily_spending_limit)
                VALUES (%s, %s)
                RETURNING daily_spending_limit
            '''
            result = run_query(sql, (user_id, 30.0), fetch_one=True)
            daily_limit = float(result['daily_spending_limit']) if result else 30.0
        
        # Cache the result
        set_cached_data(cache_key, daily_limit, max_age_seconds=600)
        return daily_limit
        
    except Exception as e:
        logger.error(f"Error getting user daily limit: {e}")
        return 30.0  # Fallback to default

def create_default_categories(user_id):
    """Create default categories for a new user"""
    # First check if user already has categories
    existing_count = run_query(
        'SELECT COUNT(*) as count FROM categories WHERE user_id = %s',
        (user_id,),
        fetch_one=True
    )
    
    if existing_count and existing_count['count'] > 0:
        return
    
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
            pass
    
    # Create default user preferences (use ON CONFLICT to handle duplicates)
    sql = '''
        INSERT INTO user_preferences (user_id, daily_spending_limit)
        VALUES (%s, 30.00)
        ON CONFLICT (user_id) DO NOTHING
    '''
    run_query(sql, (user_id,), fetch_all=False)

# Import jsonify for error handler
from flask import jsonify
