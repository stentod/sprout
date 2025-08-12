# Email Configuration Setup

This guide explains how to configure email functionality for password reset features in your Sprout Budget Tracker.

## 📧 Gmail Configuration (Recommended)

### Step 1: Enable 2-Factor Authentication
1. Go to your [Google Account settings](https://myaccount.google.com/)
2. Navigate to **Security** > **2-Step Verification**
3. Follow the prompts to enable 2FA if not already enabled

### Step 2: Generate App Password
1. In Google Account settings, go to **Security**
2. Under "2-Step Verification", click **App passwords**
3. Select **Mail** as the app type
4. Click **Generate**
5. Copy the 16-character password (ignore spaces)

### Step 3: Configure Environment Variables
1. Copy the template: `cp env_template.txt .env`
2. Edit the `.env` file with your Gmail credentials:

```env
# Email Configuration for Password Reset
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-16-character-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
```

## 🔧 Other Email Providers

### Outlook/Hotmail
```env
MAIL_SERVER=smtp-mail.outlook.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@outlook.com
MAIL_PASSWORD=your-password
```

### Yahoo Mail
```env
MAIL_SERVER=smtp.mail.yahoo.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@yahoo.com
MAIL_PASSWORD=your-app-password
```

## 🧪 Testing Email Functionality

### 1. Start the Server
```bash
cd backend
python3 app.py
```

### 2. Test Password Reset
```bash
curl -X POST http://localhost:5001/api/auth/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}'
```

### 3. Check Server Logs
Look for:
- ✅ "Password reset email sent to ..." (success)
- ❌ "Failed to send password reset email: ..." (configuration issue)

## 🔒 Security Features

### Password Reset Flow
1. User requests password reset with email
2. System generates secure token (expires in 1 hour)
3. Token stored in database with expiration
4. Email sent with reset link
5. User clicks link, enters new password
6. Token marked as used, password updated

### Security Measures
- **One-time tokens**: Each reset token can only be used once
- **Time expiration**: Tokens expire after 1 hour
- **Secure generation**: Uses `secrets.token_urlsafe(32)`
- **Generic responses**: Same message whether email exists or not
- **Password hashing**: All passwords hashed with bcrypt

## 🚀 Production Deployment

### Environment Variables
For production, set these environment variables in your hosting platform:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-production-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@yourdomain.com
SECRET_KEY=your-super-secure-secret-key
```

### Domain Configuration
Update the reset URL in `app.py`:
```python
# Change this line:
reset_url = f"http://localhost:5001/reset-password.html?token={reset_token}"

# To your production domain:
reset_url = f"https://yourdomain.com/reset-password.html?token={reset_token}"
```

## 🎯 Features Implemented

### Frontend
- ✅ Email field added to signup form
- ✅ Login accepts username OR email
- ✅ "Forgot Password" link on login page
- ✅ Password reset form with token validation
- ✅ Form validation and error messages
- ✅ Success messages and redirects

### Backend
- ✅ Email validation with regex
- ✅ Secure password reset tokens
- ✅ Flask-Mail integration
- ✅ Database migration script
- ✅ Password reset API endpoints
- ✅ Security best practices

### Database
- ✅ Email column added to users table
- ✅ Password reset tokens table
- ✅ Database indexes for performance
- ✅ Foreign key constraints

## 🛠 Troubleshooting

### Common Issues

**"Username and Password not accepted"**
- Check Gmail App Password is correct
- Ensure 2FA is enabled
- Verify MAIL_USERNAME is your full email

**"Connection timed out"**
- Check internet connection
- Verify MAIL_SERVER and MAIL_PORT
- Check firewall settings

**"Authentication failed"**
- Double-check App Password
- Try regenerating App Password
- Ensure no spaces in password

### Disable Email (Development Mode)
To disable email sending for development:
1. Comment out `mail.send(msg)` in `send_password_reset_email()`
2. Return `True` to simulate successful sending
3. Check server logs for password reset tokens

## 📱 User Experience

### Signup Flow
1. User enters username, email, password
2. Email validation on frontend and backend
3. Account created with email stored
4. Success message displayed

### Password Reset Flow
1. User clicks "Forgot Password" on login
2. Enters email address
3. Receives email with reset link
4. Clicks link, enters new password
5. Redirected to login with success message

This implementation provides a professional-grade authentication system perfect for your resume portfolio! 🌱
