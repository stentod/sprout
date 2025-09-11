from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_mail import Mail
from datetime import timedelta
import os

from utils import (
    logger, setup_logging, add_security_headers_passive, 
    DatabaseConnectionError, DEBUG, DEBUG_MODE, PORT
)

# Import blueprints
from auth import auth_bp
from expenses import expenses_bp
from categories import categories_bp
from preferences import preferences_bp
from recurring_expenses import recurring_expenses_bp
from rollover_api import rollover_bp

# Initialize logging
logger = setup_logging()


# Auto-fix recurring expenses database on app startup
try:
    from auto_fix_recurring_expenses import fix_recurring_expenses_database
    logger.info("Running automatic recurring expenses database fix...")
    if fix_recurring_expenses_database():
        logger.info("✅ Recurring expenses database fix completed successfully")
    else:
        logger.warning("⚠️ Recurring expenses database fix had issues, but app will continue")
except Exception as e:
    logger.warning(f"⚠️ Could not run recurring expenses database fix: {e}. App will continue.")

# Rollover migration already completed - tables should exist

# Process recurring expenses on app startup (with delay to ensure table is committed)
try:
    import time
    time.sleep(1)  # Give the database a moment to commit the table creation
    from recurring_expenses import process_recurring_expenses
    logger.info("Processing recurring expenses on startup...")
    processed_count = process_recurring_expenses()
    logger.info(f"✅ Processed {processed_count} recurring expenses on startup")
except Exception as e:
    logger.warning(f"⚠️ Could not process recurring expenses: {e}. App will continue.")

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

# Set mail instance for auth module
from auth import set_mail_instance
set_mail_instance(mail)

# Register blueprints with URL prefixes
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(expenses_bp, url_prefix='/api')
app.register_blueprint(categories_bp, url_prefix='/api')
app.register_blueprint(preferences_bp, url_prefix='/api')
app.register_blueprint(recurring_expenses_bp, url_prefix='/api')
app.register_blueprint(rollover_bp, url_prefix='/api')

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

@app.route('/health')
def health():
    return {'status': 'ok'}

@app.route('/api/config')
def get_config():
    """Get application configuration including debug mode"""
    # Read DEBUG_MODE directly from environment to ensure it's current
    current_debug_mode = os.environ.get("DEBUG_MODE", "False").lower() == "true"
    return jsonify({
        'debug': current_debug_mode,
        'flask_debug': DEBUG
    })

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

@app.route('/history.html')
def serve_history():
    return send_from_directory(FRONTEND_DIR, 'history.html')

@app.route('/settings.html')
def serve_settings():
    return send_from_directory(FRONTEND_DIR, 'settings.html')

@app.route('/analytics.html')
def serve_analytics():
    return send_from_directory(FRONTEND_DIR, 'analytics.html')

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
