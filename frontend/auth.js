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

// Switch between login and signup tabs
function switchTab(tab) {
  const loginForm = document.getElementById('loginForm');
  const signupForm = document.getElementById('signupForm');
  const tabs = document.querySelectorAll('.auth-tab');
  
  // Remove active class from all tabs and forms
  tabs.forEach(t => t.classList.remove('active'));
  loginForm.classList.remove('active');
  signupForm.classList.remove('active');
  
  // Add active class to selected tab and form
  if (tab === 'login') {
    document.querySelector('[onclick="switchTab(\'login\')"]').classList.add('active');
    loginForm.classList.add('active');
  } else {
    document.querySelector('[onclick="switchTab(\'signup\')"]').classList.add('active');
    signupForm.classList.add('active');
  }
  
  clearMessage();
}

// Clear message
function clearMessage() {
  document.getElementById('authMessage').innerHTML = '';
}

// Show message
function showMessage(message, type = 'error') {
  const messageDiv = document.getElementById('authMessage');
  messageDiv.innerHTML = `<div class="auth-message ${type}">${message}</div>`;
  
  // Auto-hide success messages after 3 seconds
  if (type === 'success') {
    setTimeout(() => {
      messageDiv.innerHTML = '';
    }, 3000);
  }
}

// Handle login form submission
document.getElementById('loginForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const username = document.getElementById('loginUsername').value;
  const password = document.getElementById('loginPassword').value;
  
  if (!username || !password) {
    showMessage('Please enter both username and password');
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
        username: username,
        password: password
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      showMessage('Login successful! Redirecting...', 'success');
      // Store user info in localStorage for the frontend
      localStorage.setItem('sprout_user', JSON.stringify(data.user));
      // Redirect to main app after short delay
      setTimeout(() => {
        window.location.href = '/';
      }, 1000);
    } else {
      showMessage(data.error || 'Login failed');
    }
  } catch (error) {
    showMessage('Network error. Please try again.');
  } finally {
    submitButton.textContent = originalText;
    submitButton.disabled = false;
  }
});

// Handle signup form submission
document.getElementById('signupForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  
  const username = document.getElementById('signupUsername').value;
  const password = document.getElementById('signupPassword').value;
  const confirmPassword = document.getElementById('confirmPassword').value;
  
  if (!username || !password || !confirmPassword) {
    showMessage('Please fill in all fields');
    return;
  }
  
  if (username.length < 3) {
    showMessage('Username must be at least 3 characters');
    return;
  }
  
  if (password.length < 6) {
    showMessage('Password must be at least 6 characters');
    return;
  }
  
  if (password !== confirmPassword) {
    showMessage('Passwords do not match');
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
        username: username,
        password: password
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      showMessage('Account created successfully! Please log in.', 'success');
      // Switch to login tab
      switchTab('login');
      // Pre-fill username in login form
      document.getElementById('loginUsername').value = username;
    } else {
      showMessage(data.error || 'Signup failed');
    }
  } catch (error) {
    showMessage('Network error. Please try again.');
  } finally {
    submitButton.textContent = originalText;
    submitButton.disabled = false;
  }
});

// Check if user is already logged in
function checkAuthStatus() {
  // Simple check - if user data exists, redirect to main app
  const userData = localStorage.getItem('sprout_user');
  if (userData) {
    // Verify session is still valid by making a quick API call
    fetch(`${API_BASE_URL}/api/auth/me`, {
      credentials: 'include'
    }).then(response => {
      if (response.ok) {
        window.location.href = '/';
      } else {
        // Session expired, clear storage
        localStorage.removeItem('sprout_user');
      }
    }).catch(() => {
      // Network error, stay on auth page
    });
  }
}

// Check auth status when page loads
checkAuthStatus();
