#!/usr/bin/env python3
"""
Quick email test script to verify Gmail configuration.
Run this after setting up your Gmail App Password in .env file.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_email_config():
    """Test email configuration"""
    print("🧪 Testing Email Configuration...")
    
    # Get config from .env
    mail_server = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    mail_port = int(os.getenv('MAIL_PORT', 587))
    mail_username = os.getenv('MAIL_USERNAME', '')
    mail_password = os.getenv('MAIL_PASSWORD', '')
    
    print(f"📧 Server: {mail_server}:{mail_port}")
    print(f"👤 Username: {mail_username}")
    print(f"🔑 Password: {'*' * len(mail_password) if mail_password else 'NOT SET'}")
    
    if not mail_username or not mail_password or 'REPLACE_WITH' in mail_password:
        print("❌ Email credentials not properly configured!")
        print("📝 Please update your .env file with your Gmail App Password")
        return False
    
    try:
        print("\n🔄 Connecting to Gmail SMTP...")
        
        # Create SMTP connection
        server = smtplib.SMTP(mail_server, mail_port)
        server.starttls()  # Enable encryption
        
        print("🔐 Authenticating...")
        server.login(mail_username, mail_password)
        
        print("📨 Sending test email...")
        
        # Create test email
        msg = MIMEMultipart()
        msg['From'] = mail_username
        msg['To'] = mail_username  # Send to yourself
        msg['Subject'] = "🌱 Sprout Budget Tracker - Email Test"
        
        body = """Hello!

This is a test email from your Sprout Budget Tracker application.

If you received this email, your password reset functionality is working correctly! 🎉

Features tested:
✅ SMTP connection to Gmail
✅ TLS encryption
✅ Authentication with App Password
✅ Email sending

Your password reset emails will now be delivered successfully.

Best regards,
The Sprout Team"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        text = msg.as_string()
        server.sendmail(mail_username, mail_username, text)
        server.quit()
        
        print("✅ SUCCESS! Test email sent successfully!")
        print(f"📬 Check your inbox: {mail_username}")
        print("🎉 Password reset emails will now work!")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print("\n🔧 Common fixes:")
        print("1. Make sure 2-Step Verification is enabled in Gmail")
        print("2. Generate a new App Password at: https://myaccount.google.com/security")
        print("3. Use the App Password (not your regular Gmail password)")
        print("4. Remove any spaces from the App Password")
        
        return False

if __name__ == "__main__":
    test_email_config()
