// Get API base URL - same as other frontend files
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

// Extract token from URL
function getTokenFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('token');
}

// Message display functions
function clearMessage() {
    const messageDiv = document.getElementById('resetMessage');
    messageDiv.textContent = '';
    messageDiv.className = '';
}

function showMessage(message, type = 'info') {
    const messageDiv = document.getElementById('resetMessage');
    messageDiv.innerHTML = `<div class="auth-message ${type}">${message}</div>`;
}

// Form submission
document.getElementById('resetPasswordForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const token = getTokenFromUrl();
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const resetButton = document.getElementById('resetButton');
    
    // Clear previous messages
    clearMessage();
    
    // Validation
    if (!token) {
        showMessage('Invalid reset link. Please request a new password reset.', 'error');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showMessage('Passwords do not match.', 'error');
        return;
    }
    
    if (newPassword.length < 6) {
        showMessage('Password must be at least 6 characters long.', 'error');
        return;
    }
    
    // Disable button and show loading state
    resetButton.disabled = true;
    resetButton.textContent = 'Resetting...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                token: token,
                password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage(data.message, 'success');
            
            // Redirect to login page after 3 seconds
            setTimeout(() => {
                window.location.href = '/auth.html?message=password-reset-success';
            }, 3000);
        } else {
            showMessage(data.error || 'Password reset failed', 'error');
        }
    } catch (error) {
        console.error('Reset password error:', error);
        showMessage('Network error. Please try again.', 'error');
    } finally {
        // Re-enable button
        resetButton.disabled = false;
        resetButton.textContent = 'Reset Password';
    }
});

// Check if token exists on page load
document.addEventListener('DOMContentLoaded', function() {
    const token = getTokenFromUrl();
    if (!token) {
        showMessage('Invalid reset link. Please request a new password reset from the login page.', 'error');
        document.getElementById('resetPasswordForm').style.display = 'none';
    }
});
