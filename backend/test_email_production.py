#!/usr/bin/env python3
"""
Test script to debug email configuration in production
"""
import os
from dotenv import load_dotenv
from flask_mail import Mail, Message

# Load environment variables
load_dotenv()

def test_email_config():
    """Test email configuration"""
    print("🔍 Testing Email Configuration...")
    print("=" * 50)
    
    # Check environment variables
    print("📧 Email Configuration:")
    print(f"MAIL_SERVER: {os.environ.get('MAIL_SERVER', 'NOT SET')}")
    print(f"MAIL_PORT: {os.environ.get('MAIL_PORT', 'NOT SET')}")
    print(f"MAIL_USE_TLS: {os.environ.get('MAIL_USE_TLS', 'NOT SET')}")
    print(f"MAIL_USERNAME: {os.environ.get('MAIL_USERNAME', 'NOT SET')}")
    print(f"MAIL_PASSWORD: {'SET' if os.environ.get('MAIL_PASSWORD') else 'NOT SET'}")
    print(f"MAIL_DEFAULT_SENDER: {os.environ.get('MAIL_DEFAULT_SENDER', 'NOT SET')}")
    print(f"BASE_URL: {os.environ.get('BASE_URL', 'NOT SET')}")
    print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'NOT SET')}")
    
    print("\n" + "=" * 50)
    
    # Check if we can create a Flask app and Mail instance
    try:
        from flask import Flask
        app = Flask(__name__)
        
        # Configure Flask-Mail
        app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
        app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
        app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
        app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL', 'False').lower() == 'true'
        app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
        app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
        app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])
        
        mail = Mail(app)
        print("✅ Flask-Mail configuration successful")
        
        # Test creating a message
        with app.app_context():
            msg = Message(
                subject="Test Email",
                recipients=["test@example.com"],
                body="This is a test email"
            )
            print("✅ Message creation successful")
            
            # Don't actually send, just test configuration
            print("✅ Email configuration appears valid")
            
    except Exception as e:
        print(f"❌ Email configuration error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 50)
    print("🔧 Troubleshooting Tips:")
    print("1. Check if MAIL_USERNAME and MAIL_PASSWORD are set correctly")
    print("2. Verify Gmail App Password is still valid (they can expire)")
    print("3. Make sure BASE_URL is set to your production domain")
    print("4. Check if FLASK_ENV=production is set")
    print("5. Verify your .env file is being loaded in production")

if __name__ == "__main__":
    test_email_config()
