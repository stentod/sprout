from flask import Blueprint, request, jsonify, session
from flask_mail import Message
import sendgrid
from sendgrid.helpers.mail import Mail as SendGridMail
from datetime import datetime, timedelta, timezone
import os

from utils import (
    logger, run_query, hash_password, verify_password, validate_email, 
    generate_reset_token, validate_auth_data, handle_errors, 
    log_security_event, create_default_categories, DatabaseError, 
    AuthenticationError, ValidationError
)

# Create Blueprint for auth routes
auth_bp = Blueprint('auth', __name__)

# Email configuration - will be imported after app creation
mail = None

def set_mail_instance(mail_instance):
    """Set the mail instance from main app"""
    global mail
    mail = mail_instance

def send_password_reset_email_sendgrid(user_email, username, reset_token):
    """Send password reset email using SendGrid (Professional)"""
    try:
        # Get SendGrid API key from environment
        sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
        if not sendgrid_api_key:
            logger.info("SendGrid API key not configured, falling back to Gmail")
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
        return True
        
    except Exception as e:
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
        return True
    except Exception as e:
        return False

def send_password_reset_email(user_email, username, reset_token):
    """Send password reset email (tries SendGrid first, falls back to Gmail)"""
    # Check environment variables
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    
    return send_password_reset_email_sendgrid(user_email, username, reset_token)

def require_auth(f):
    """Decorator to require authentication for protected routes"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_id():
    """Get the current user's ID from session"""
    return session.get('user_id')

# Authentication Routes
@auth_bp.route('/signup', methods=['POST'])
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

@auth_bp.route('/login', methods=['POST'])
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

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """User logout"""
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/me', methods=['GET'])
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
        logger.error(f"Get current user error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Initiate password reset process"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email address is required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Please enter a valid email address'}), 400
        
        # Check if user exists
        user = run_query(
            'SELECT id, email FROM users WHERE email = %s',
            (email,),
            fetch_one=True
        )
        
        if user:
            # Generate reset token
            reset_token = generate_reset_token()
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)  # Token expires in 1 hour
            
            # Store token in database
            sql = '''
                INSERT INTO password_reset_tokens (user_id, token, expires_at)
                VALUES (%s, %s, %s)
            '''
            run_query(sql, (user['id'], reset_token, expires_at), fetch_all=False)
            
            # Send email (use email as display name since no username)
            email_sent = send_password_reset_email(user['email'], user['email'], reset_token)
        
        # Always return the same message for security
        return jsonify({
            'message': 'If an account with that email exists, we\'ve sent password reset instructions.'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@auth_bp.route('/reset-password', methods=['POST'])
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
        
        return jsonify({'message': 'Password reset successful! You can now log in with your new password.'}), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500
