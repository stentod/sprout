from flask import Flask, request, jsonify, send_from_directory, session
from flask_compress import Compress
from flask_cors import CORS
from flask_mail import Mail, Message
import sendgrid
from sendgrid.helpers.mail import Mail as SendGridMail
import psycopg2
import psycopg2.extras
from psycopg2 import pool
import os
import bcrypt
import secrets
import re
import logging
import logging.handlers
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from functools import wraps, lru_cache
import re
import time

# Load environment variables (for local development)
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

# ==========================================
# DATABASE CONNECTION POOLING
# ==========================================

# Global connection pool
_connection_pool = None

def init_connection_pool():
    """Initialize the database connection pool"""
    global _connection_pool
    try:
        DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://dstent@localhost/sprout_budget")
        
        # Create connection pool with reasonable defaults
        _connection_pool = pool.SimpleConnectionPool(
            minconn=1,      # Minimum connections
            maxconn=10,     # Maximum connections
            dsn=DATABASE_URL
        )
        logger.info("Database connection pool initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e}")
        return False

def get_pooled_connection():
    """Get a connection from the pool"""
    global _connection_pool
    if _connection_pool is None:
        # Fallback to direct connection if pool not initialized
        return get_db_connection()
    
    try:
        return _connection_pool.getconn()
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e}")
        # Fallback to direct connection
        return get_db_connection()

def return_pooled_connection(conn):
    """Return a connection to the pool"""
    global _connection_pool
    if _connection_pool is not None and conn is not None:
        try:
            _connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e}")
            # Close connection if we can't return it to pool
            try:
                conn.close()
            except:
                pass

def log_with_context(level, message, **context):
    """Helper function for structured logging with context"""
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

# Production fix - ensure proper session handling
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Enhanced session configuration for production
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Sessions last 7 days

# ==========================================
# RESPONSE COMPRESSION
# ==========================================

# Initialize compression for better performance
Compress(app)

# Set session cookie domain for custom domains (commented out for now)
# if os.environ.get('FLASK_ENV') == 'production':
#     # Allow session cookies to work with custom domains
#     app.config['SESSION_COOKIE_DOMAIN'] = None  # Let Flask auto-detect
CORS(app, supports_credentials=True)

# Passive security headers - won't interfere with functionality
@app.after_request
def add_security_headers(response):
    """Add passive security headers"""
    return add_security_headers_passive(response)

# Email configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

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
    Helper function to run database queries with proper connection handling and pooling
    
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
        # Use connection pool if available, fallback to direct connection
        conn = get_pooled_connection()
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
            # Return connection to pool instead of closing
            return_pooled_connection(conn)

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
            SELECT e.amount, e.description, e.timestamp, e.category_id,
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
            'amount': float(e['amount']),
            'description': e['description'],
            'timestamp': e['timestamp'].isoformat() if hasattr(e['timestamp'], 'isoformat') else str(e['timestamp'])
        }
        
        # Add category information if present
        if e['category_id'] and e['category_name']:
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
            print(f"🔍 Budget tracking for user_id: {user_id}")
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
            print(f"📊 Found {len(categories)} categories for user {user_id}")
            budgeted_count = sum(1 for cat in categories if cat['daily_budget'] > 0)
            print(f"💰 {budgeted_count} categories have budgets")
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
            spending_data = run_query(spending_sql, (user_id, today_start.isoformat(), today_end.isoformat()), fetch_all=True)
        except Exception as db_error:
            print(f"Database error getting spending data: {db_error}")
            spending_data = []
        
        # Create spending lookup with debugging
        spending_by_category = {}
        print(f"💸 Found {len(spending_data)} spending records")
        for row in spending_data:
            category_id = row['category_id']
            spent = float(row['total_spent'])
            spending_by_category[category_id] = spent
            print(f"   💸 Spending: {category_id} = ${spent}")
        
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
                print(f"   💰 {cat['name']} ({cat['id']}): ${budget} budget, ${spent} spent, ${remaining} remaining")
                print(f"      🔍 Debug: budget={budget} (type: {type(budget)}), spent={spent} (type: {type(spent)}), remaining={remaining}")
                
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
@handle_errors
def add_expense():
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
            category_id = int(cat_id)
        else:
            # Legacy format - assume it's a custom category
            category_id = int(category_id)
            category_type = 'custom'
        
        logger.debug("Validating category", extra={
            'user_id': user_id,
            'category_type': category_type,
            'category_id': category_id
        })
        
        if category_type == 'default':
            # Check if default category exists
            check_sql = 'SELECT id FROM default_categories WHERE id = %s'
            category_exists = run_query(check_sql, (category_id,), fetch_one=True)
        else:
            # Check if custom category exists and belongs to the user
            check_sql = 'SELECT id FROM custom_categories WHERE id = %s AND user_id = %s'
            category_exists = run_query(check_sql, (category_id, user_id), fetch_one=True)
        
        if not category_exists:
            logger.warning("Invalid category provided", extra={
                'user_id': user_id,
                'category_type': category_type,
                'category_id': category_id
            })
            raise ValidationError("Invalid category", field="category_id")
        logger.debug("Category validated successfully", extra={
            'user_id': user_id,
            'category_type': category_type,
            'category_id': category_id
        })
    else:
        logger.info("No category provided, expense will be saved without category", extra={
            'user_id': user_id
        })
    
    # Use UTC timestamp to ensure consistent date handling across timezones
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    logger.debug("Generated timestamp for expense", extra={
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
            storage_category_id = f"default_{category_id}"
        else:
            storage_category_id = f"custom_{category_id}"
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
        
        # OPTIMIZED: Get 7-day spending data in a single query
        start_date, _ = get_day_bounds(day_offset - 6)  # 7 days ago
        _, end_date = get_day_bounds(day_offset + 1)    # Tomorrow
        
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
                day_start, day_end = get_day_bounds(offset)
                date_key = day_start.strftime('%Y-%m-%d')
                daily_spent = spending_lookup.get(date_key, 0.0)
                daily_surplus = user_daily_limit - daily_spent
                deltas.append(daily_surplus)
                
        except Exception as e:
            print(f"Error getting 7-day spending data: {e}, using defaults")
            # Fallback to default values
            deltas = [user_daily_limit] * 7
        
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
    """Get expense history with pagination and optimized queries - PHASE 3"""
    try:
        # Get parameters with pagination support
        day_offset = int(request.args.get('dayOffset', 0))
        period = int(request.args.get('period', 7))  # Default to 7 days
        category_id = request.args.get('category_id')  # Optional category filter
        page = int(request.args.get('page', 1))  # Page number (1-based)
        per_page = int(request.args.get('per_page', 50))  # Items per page (max 100)
        
        # Limit per_page to prevent abuse
        per_page = min(per_page, 100)
        per_page = max(per_page, 1)
        
        user_id = get_current_user_id()
        start_date, _ = get_day_bounds(day_offset - (period - 1))
        _, end_date = get_day_bounds(day_offset)
        
        try:
            # OPTIMIZED: Use pagination and more efficient query
            offset = (page - 1) * per_page
            
            if category_id:
                # Filtered query with pagination
                history_sql = '''
                    SELECT e.amount, e.description, e.timestamp, e.category_id,
                           COALESCE(dc.name, cc.name) as category_name,
                           COALESCE(dc.icon, cc.icon) as category_icon,
                           COALESCE(dc.color, cc.color) as category_color,
                           COUNT(*) OVER() as total_count
                    FROM expenses e
                    LEFT JOIN default_categories dc ON e.category_id = CONCAT('default_', dc.id::text)
                    LEFT JOIN custom_categories cc ON e.category_id = CONCAT('custom_', cc.id::text) AND cc.user_id = e.user_id
                    WHERE e.user_id = %s AND e.timestamp >= %s AND e.timestamp < %s AND e.category_id = %s
                    ORDER BY e.timestamp DESC
                    LIMIT %s OFFSET %s
                '''
                params = (user_id, start_date.isoformat(), end_date.isoformat(), category_id, per_page, offset)
            else:
                # Unfiltered query with pagination
                history_sql = '''
                    SELECT e.amount, e.description, e.timestamp, e.category_id,
                           COALESCE(dc.name, cc.name) as category_name,
                           COALESCE(dc.icon, cc.icon) as category_icon,
                           COALESCE(dc.color, cc.color) as category_color,
                           COUNT(*) OVER() as total_count
                    FROM expenses e
                    LEFT JOIN default_categories dc ON e.category_id = CONCAT('default_', dc.id::text)
                    LEFT JOIN custom_categories cc ON e.category_id = CONCAT('custom_', cc.id::text) AND cc.user_id = e.user_id
                    WHERE e.user_id = %s AND e.timestamp >= %s AND e.timestamp < %s
                    ORDER BY e.timestamp DESC
                    LIMIT %s OFFSET %s
                '''
                params = (user_id, start_date.isoformat(), end_date.isoformat(), per_page, offset)
            
            expenses_raw = run_query(history_sql, params, fetch_all=True)
            
            if not expenses_raw:
                return jsonify({
                    'data': [],
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total_count': 0,
                        'total_pages': 0,
                        'has_next': False,
                        'has_prev': False
                    }
                })
            
            # Get total count from first row
            total_count = expenses_raw[0]['total_count'] if expenses_raw else 0
            total_pages = (total_count + per_page - 1) // per_page
            
            # Process expenses
            expenses = []
            for e in expenses_raw:
                expense_data = {
                    'amount': float(e['amount']),
                    'description': e['description'],
                    'timestamp': e['timestamp'].isoformat() if hasattr(e['timestamp'], 'isoformat') else str(e['timestamp'])
                }
                
                # Add category information if present
                if e['category_id'] and e['category_name']:
                    expense_data['category'] = {
                        'id': e['category_id'],
                        'name': e['category_name'],
                        'icon': e['category_icon'],
                        'color': e['category_color']
                    }
                else:
                    expense_data['category'] = None
                    
                expenses.append(expense_data)
            
            # Group by date (YYYY-MM-DD)
            grouped = {}
            for e in expenses:
                date = e['timestamp'][:10]  # 'YYYY-MM-DD'
                if date not in grouped:
                    grouped[date] = []
                grouped[date].append(e)
            
            # Sort by date descending
            grouped_sorted = [
                {'date': date, 'expenses': grouped[date]}
                for date in sorted(grouped.keys(), reverse=True)
            ]
            
            return jsonify({
                'data': grouped_sorted,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            })
            
        except Exception as e:
            print(f"Error getting paginated expenses: {e}")
            # Return empty history with pagination info instead of crashing
            return jsonify({
                'data': [],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total_count': 0,
                    'total_pages': 0,
                    'has_next': False,
                    'has_prev': False
                }
            })
        
    except Exception as e:
        print(f"History endpoint error: {e}")
        import traceback
        traceback.print_exc()
        # Return empty history instead of crashing
        return jsonify([])

# Helper function to get user's daily spending limit (OPTIMIZED with caching)
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
@handle_errors
def signup():
    """User registration with email-only authentication"""
    # Enhanced request parsing with better error handling
    if not request.is_json:
        raise ValidationError("Request must be JSON")
        
    data = request.get_json()
    validated_data = validate_auth_data(data)
    email = validated_data['email']
    password = validated_data['password']
    
    # Passive security logging - doesn't affect functionality
    log_security_event('signup_attempt', {'email': email})
    
    logger.info("Signup attempt", extra={'email': email})
    
    # Check if email already exists
    existing_email = run_query(
        'SELECT id FROM users WHERE email = %s',
        (email,),
        fetch_one=True
    )
    if existing_email:
        logger.warning("Signup failed - email already exists", extra={'email': email})
        raise ValidationError("An account with this email already exists. Please use a different email or try logging in.")
    
    # Hash password and create user
    password_hash = hash_password(password)
    sql = '''
        INSERT INTO users (email, password_hash)
        VALUES (%s, %s)
        RETURNING id, email
    '''
    result = run_query(sql, (email, password_hash), fetch_one=True)
    
    if not result:
        raise DatabaseError("Failed to create account. Please try again.")
        
    user_id = result['id']
    logger.info("User created successfully", extra={'user_id': user_id, 'email': email})
    
    # Create default categories and preferences for new user
    try:
        create_default_categories(user_id)
        logger.info("Default categories created", extra={'user_id': user_id})
    except Exception as cat_error:
        # If categories creation fails, delete the user to maintain consistency
        logger.error("Failed to create default categories, rolling back user creation", extra={
            'user_id': user_id,
            'error': str(cat_error)
        })
        try:
            delete_sql = 'DELETE FROM users WHERE id = %s'
            run_query(delete_sql, (user_id,), fetch_all=False)
            logger.info("User creation rolled back", extra={'user_id': user_id})
        except Exception as delete_error:
            logger.error("Failed to rollback user creation", extra={
                'user_id': user_id,
                'error': str(delete_error)
            })
        raise DatabaseError("Failed to set up account. Please try again.")
    
    # Automatically log the user in after successful signup
    session.clear()  # Clear any existing session
    session['user_id'] = user_id
    session.permanent = True  # Make session persistent
    
    logger.info("User automatically logged in after signup", extra={'user_id': user_id})
    
    return jsonify({
        'message': 'Account created successfully! You are now logged in.',
        'user': {
            'id': result['id'],
            'email': result['email']
        },
        'auto_login': True
    }), 201

@app.route('/api/auth/login', methods=['POST'])
@handle_errors
def login():
    """User login with email and password"""
    # Enhanced request parsing with better error handling
    if not request.is_json:
        raise ValidationError("Request must be JSON")
        
    data = request.get_json()
    validated_data = validate_auth_data(data)
    email = validated_data['email']
    password = validated_data['password']
    
    # Passive security logging - doesn't affect functionality
    log_security_event('login_attempt', {'email': email})
    
    logger.info("Login attempt", extra={'email': email})
    
    # Login with email
    sql = 'SELECT id, email, password_hash FROM users WHERE email = %s'
    user = run_query(sql, (email,), fetch_one=True)
    
    if not user:
        logger.warning("Login failed - no user found", extra={'email': email})
        raise AuthenticationError("Invalid email or password")
        
    logger.debug("User found", extra={'user_id': user['id'], 'email': user['email']})
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        logger.warning("Login failed - invalid password", extra={'email': email})
        raise AuthenticationError("Invalid email or password")
    
    # Set session with enhanced session management
    session.clear()  # Clear any existing session data
    session['user_id'] = user['id']
    session['email'] = user['email']
    session.permanent = True  # Make session permanent
    
    logger.info("Login successful", extra={'user_id': user['id'], 'email': user['email']})
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'email': user['email']
        }
    }), 200

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

@app.route('/api/debug/budget-tracking')
@require_auth
def debug_budget_tracking():
    """Debug endpoint to show budget tracking data in a readable format"""
    try:
        user_id = get_current_user_id()
        day_offset = int(request.args.get('dayOffset', 0))
        today_start, today_end = get_day_bounds(day_offset)
        
        # Get categories with budgets
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
        
        # Get spending data
        spending_sql = '''
            SELECT 
                CASE 
                    WHEN e.category_id LIKE 'default_%%' THEN e.category_id
                    WHEN e.category_id LIKE 'custom_%%' THEN e.category_id
                    ELSE CONCAT('default_', e.category_id)
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
        
        spending_by_category = {row['category_id']: float(row['total_spent']) for row in spending_data}
        
        # Build debug response
        debug_data = {
            'user_id': user_id,
            'date_range': {
                'start': today_start.isoformat(),
                'end': today_end.isoformat()
            },
            'categories': [],
            'spending_by_category': spending_by_category,
            'summary': {
                'total_categories': len(categories),
                'categories_with_budgets': 0,
                'total_budget': 0,
                'total_spent': sum(spending_by_category.values())
            }
        }
        
        for cat in categories:
            budget = float(cat['daily_budget']) if cat['daily_budget'] else 0.0
            spent = spending_by_category.get(cat['id'], 0.0)
            remaining = budget - spent if budget > 0 else 0
            
            category_debug = {
                'id': cat['id'],
                'name': cat['name'],
                'budget': budget,
                'spent': spent,
                'remaining': remaining,
                'has_budget': budget > 0
            }
            
            debug_data['categories'].append(category_debug)
            
            if budget > 0:
                debug_data['summary']['categories_with_budgets'] += 1
                debug_data['summary']['total_budget'] += budget
        
        return jsonify(debug_data)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
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
        print(f"Error deleting custom category: {e}")
        return jsonify({
            'error': str(e),
            'success': False
        }), 500

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
    # Initialize connection pool before starting the server
    print("🌱 Initializing database connection pool...")
    if init_connection_pool():
        print("✅ Connection pool initialized successfully")
    else:
        print("⚠️  Connection pool initialization failed, using direct connections")
    
    # Only run the development server if this file is run directly
    # In production, gunicorn will import and run the app
    app.run(debug=DEBUG, port=PORT, host='0.0.0.0') 