#!/usr/bin/env python3
"""
Debug script to check email configuration in production
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_email_config():
    """Check email configuration"""
    print("🔍 Checking Email Configuration...")
    print("=" * 50)
    
    # Check Gmail configuration
    print("📧 Gmail Configuration:")
    mail_server = os.environ.get('MAIL_SERVER')
    mail_port = os.environ.get('MAIL_PORT')
    mail_username = os.environ.get('MAIL_USERNAME')
    mail_password = os.environ.get('MAIL_PASSWORD')
    mail_default_sender = os.environ.get('MAIL_DEFAULT_SENDER')
    
    print(f"  MAIL_SERVER: {mail_server}")
    print(f"  MAIL_PORT: {mail_port}")
    print(f"  MAIL_USERNAME: {mail_username}")
    print(f"  MAIL_PASSWORD: {'***SET***' if mail_password else 'NOT SET'}")
    print(f"  MAIL_DEFAULT_SENDER: {mail_default_sender}")
    
    # Check SendGrid configuration
    print("\n📧 SendGrid Configuration:")
    sendgrid_api_key = os.environ.get('SENDGRID_API_KEY')
    from_email = os.environ.get('FROM_EMAIL')
    
    print(f"  SENDGRID_API_KEY: {'***SET***' if sendgrid_api_key else 'NOT SET'}")
    print(f"  FROM_EMAIL: {from_email}")
    
    # Check app configuration
    print("\n🌐 App Configuration:")
    base_url = os.environ.get('BASE_URL')
    flask_env = os.environ.get('FLASK_ENV')
    
    print(f"  BASE_URL: {base_url}")
    print(f"  FLASK_ENV: {flask_env}")
    
    # Test Flask-Mail configuration
    print("\n🧪 Testing Flask-Mail Configuration:")
    try:
        from flask import Flask
        from flask_mail import Mail
        
        app = Flask(__name__)
        app.config['MAIL_SERVER'] = mail_server
        app.config['MAIL_PORT'] = int(mail_port) if mail_port else 587
        app.config['MAIL_USE_TLS'] = True
        app.config['MAIL_USE_SSL'] = False
        app.config['MAIL_USERNAME'] = mail_username
        app.config['MAIL_PASSWORD'] = mail_password
        app.config['MAIL_DEFAULT_SENDER'] = mail_default_sender
        
        mail = Mail(app)
        print("  ✅ Flask-Mail configuration is valid")
        
        # Test if we can create a message
        from flask_mail import Message
        msg = Message(
            subject="Test Email",
            recipients=["test@example.com"],
            body="This is a test email"
        )
        print("  ✅ Can create email message")
        
    except Exception as e:
        print(f"  ❌ Flask-Mail configuration error: {e}")
    
    # Test SendGrid configuration
    print("\n🧪 Testing SendGrid Configuration:")
    try:
        if sendgrid_api_key:
            import sendgrid
            from sendgrid.helpers.mail import Mail as SendGridMail
            
            sg = sendgrid.SendGridAPIClient(api_key=sendgrid_api_key)
            print("  ✅ SendGrid client created successfully")
            
            # Test creating a message
            message = SendGridMail(
                from_email=from_email or 'test@example.com',
                to_emails='test@example.com',
                subject='Test Email',
                html_content='<p>This is a test email</p>'
            )
            print("  ✅ Can create SendGrid message")
        else:
            print("  ⚠️ SendGrid API key not configured")
            
    except Exception as e:
        print(f"  ❌ SendGrid configuration error: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 SUMMARY:")
    
    gmail_configured = all([mail_server, mail_username, mail_password])
    sendgrid_configured = bool(sendgrid_api_key)
    
    if gmail_configured:
        print("  ✅ Gmail configuration is complete")
    else:
        print("  ❌ Gmail configuration is incomplete")
        missing = []
        if not mail_server: missing.append('MAIL_SERVER')
        if not mail_username: missing.append('MAIL_USERNAME')
        if not mail_password: missing.append('MAIL_PASSWORD')
        print(f"     Missing: {', '.join(missing)}")
    
    if sendgrid_configured:
        print("  ✅ SendGrid configuration is complete")
    else:
        print("  ❌ SendGrid configuration is incomplete")
        print("     Missing: SENDGRID_API_KEY")
    
    if gmail_configured or sendgrid_configured:
        print("  ✅ Email sending should work")
    else:
        print("  ❌ No email configuration found - password reset will fail")
        print("\n🔧 To fix this:")
        print("  1. Set up Gmail App Password in Render environment variables")
        print("  2. Or set up SendGrid API key in Render environment variables")

if __name__ == "__main__":
    check_email_config()
