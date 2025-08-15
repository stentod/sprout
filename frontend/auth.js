// Get API base URL - same as main.js
function getApiBaseUrl() {
  const isDevelopment = window.location.hostname === 'localhost' && window.location.port !== '';
  const isLivereload = window.location.port === '8080' || window.location.port === '3000';
  
  if (isDevelopment && isLivereload) {
    const apiPort = window.ENV_API_PORT || '5001';
    return `http://localhost:${apiPort}`;
  }
  
  return '';
}

const API_BASE_URL = getApiBaseUrl();

// Switch between login, signup, and forgot password tabs
function switchTab(tab) {
  const loginForm = document.getElementById('loginForm');
  const signupForm = document.getElementById('signupForm');
  const forgotForm = document.getElementById('forgotPasswordForm');
  const tabs = document.querySelectorAll('.auth-tab');
  
  // Remove active class from all tabs and forms
  tabs.forEach(t => t.classList.remove('active'));
  loginForm.classList.remove('active');
  signupForm.classList.remove('active');
  forgotForm.classList.remove('active');
  
  // Add active class to selected tab and form
  if (tab === 'login') {
    document.querySelector('[data-tab="login"]').classList.add('active');
    loginForm.classList.add('active');
  } else if (tab === 'signup') {
    document.querySelector('[data-tab="signup"]').classList.add('active');
    signupForm.classList.add('active');
  } else if (tab === 'forgot') {
    // Show forgot password form
    forgotForm.classList.add('active');
  }
  
  clearMessage();
}

// Clear message
function clearMessage() {
  const messages = document.querySelectorAll('.auth-message');
  messages.forEach(msg => msg.innerHTML = '');
}

// Show message
function showMessage(message, type = 'error', formId = 'loginForm') {
  const messageDiv = document.getElementById(formId).querySelector('.auth-message');
  if (messageDiv) {
    messageDiv.innerHTML = `<div class="auth-message ${type}">${message}</div>`;
    
    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
      setTimeout(() => {
        messageDiv.innerHTML = '';
      }, 5000);
    }
  }
}

// Email validation
function validateEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

// Handle login form submission
document.getElementById('loginForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const email = document.getElementById('loginEmail').value.trim().toLowerCase();
  const password = document.getElementById('loginPassword').value;
  
  if (!email || !password) {
    showMessage('Please enter both email and password', 'error', 'loginForm');
    return;
  }
  
  if (!validateEmail(email)) {
    showMessage('Please enter a valid email address', 'error', 'loginForm');
    return;
  }
  
  const submitButton = this.querySelector('button[type="submit"]');
  const originalText = submitButton.textContent;
  submitButton.textContent = 'Logging in...';
  submitButton.disabled = true;
  clearMessage();
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Include cookies for session
      body: JSON.stringify({
        email: email,
        password: password
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      showMessage('Login successful! Redirecting...', 'success', 'loginForm');
      // Store user data in localStorage for frontend use
      localStorage.setItem('user', JSON.stringify(data.user));
      // Redirect to main dashboard
      setTimeout(() => {
        window.location.href = '/';
      }, 1000);
    } else {
      showMessage(data.error || 'Login failed. Please try again.', 'error', 'loginForm');
    }
  } catch (error) {
    console.error('Login error:', error);
    showMessage('Network error. Please check your connection and try again.', 'error', 'loginForm');
  } finally {
    submitButton.textContent = originalText;
    submitButton.disabled = false;
  }
});

// Handle signup form submission
document.getElementById('signupForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const email = document.getElementById('signupEmail').value.trim().toLowerCase();
  const password = document.getElementById('signupPassword').value;
  const confirmPassword = document.getElementById('signupConfirmPassword').value;
  
  if (!email || !password || !confirmPassword) {
    showMessage('Please fill in all fields', 'error', 'signupForm');
    return;
  }
  
  if (!validateEmail(email)) {
    showMessage('Please enter a valid email address', 'error', 'signupForm');
    return;
  }
  
  if (password.length < 6) {
    showMessage('Password must be at least 6 characters long', 'error', 'signupForm');
    return;
  }
  
  if (password !== confirmPassword) {
    showMessage('Passwords do not match', 'error', 'signupForm');
    return;
  }
  
  const submitButton = this.querySelector('button[type="submit"]');
  const originalText = submitButton.textContent;
  submitButton.textContent = 'Creating account...';
  submitButton.disabled = true;
  clearMessage();
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/signup`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        email: email,
        password: password
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      if (data.auto_login) {
        // User was automatically logged in
        showMessage('Account created successfully! You are now logged in.', 'success', 'signupForm');
        localStorage.setItem('user', JSON.stringify(data.user));
        setTimeout(() => {
          window.location.href = '/';
        }, 1000);
      } else {
        // User needs to log in manually
        showMessage('Account created successfully! Please log in.', 'success', 'signupForm');
        setTimeout(() => {
          switchTab('login');
        }, 2000);
      }
    } else {
      showMessage(data.error || 'Signup failed. Please try again.', 'error', 'signupForm');
    }
  } catch (error) {
    console.error('Signup error:', error);
    showMessage('Network error. Please check your connection and try again.', 'error', 'signupForm');
  } finally {
    submitButton.textContent = originalText;
    submitButton.disabled = false;
  }
});

// Handle forgot password form submission
document.getElementById('forgotPasswordForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const email = document.getElementById('forgotEmail').value.trim().toLowerCase();
  
  if (!email) {
    showMessage('Please enter your email address', 'error', 'forgotPasswordForm');
    return;
  }
  
  if (!validateEmail(email)) {
    showMessage('Please enter a valid email address', 'error', 'forgotPasswordForm');
    return;
  }
  
  const submitButton = this.querySelector('button[type="submit"]');
  const originalText = submitButton.textContent;
  submitButton.textContent = 'Sending...';
  submitButton.disabled = true;
  clearMessage();
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/forgot-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({
        email: email
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      showMessage(data.message || 'Password reset instructions sent to your email.', 'success', 'forgotPasswordForm');
      // Clear the form
      document.getElementById('forgotEmail').value = '';
    } else {
      showMessage(data.error || 'Failed to send reset instructions. Please try again.', 'error', 'forgotPasswordForm');
    }
  } catch (error) {
    console.error('Forgot password error:', error);
    showMessage('Network error. Please check your connection and try again.', 'error', 'forgotPasswordForm');
  } finally {
    submitButton.textContent = originalText;
    submitButton.disabled = false;
  }
});

// Add event listeners for tab switching
document.addEventListener('DOMContentLoaded', function() {
  // Tab switching
  const tabs = document.querySelectorAll('.auth-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', function() {
      const tabName = this.getAttribute('data-tab');
      switchTab(tabName);
    });
  });
  
  // Forgot password link
  const forgotPasswordLink = document.querySelector('.forgot-password-link');
  if (forgotPasswordLink) {
    forgotPasswordLink.addEventListener('click', function(e) {
      e.preventDefault();
      switchTab('forgot');
    });
  }
  
  // Back to login link
  const backToLoginLink = document.querySelector('.back-to-login-link');
  if (backToLoginLink) {
    backToLoginLink.addEventListener('click', function(e) {
      e.preventDefault();
      switchTab('login');
    });
  }
  
  // Check if user is already logged in
  checkAuthentication();
});

// Check if user is already authenticated
async function checkAuthentication() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
      credentials: 'include'
    });
    
    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('user', JSON.stringify(data.user));
      // User is already logged in, redirect to dashboard
      window.location.href = '/';
    }
  } catch (error) {
    // User is not logged in, stay on auth page
    console.log('User not authenticated');
  }
}
