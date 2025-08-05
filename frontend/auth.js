// Authentication JavaScript
class AuthManager {
    constructor() {
        this.apiBaseUrl = 'http://localhost:5001/api';
        this.token = localStorage.getItem('sprout_token');
        this.user = JSON.parse(localStorage.getItem('sprout_user') || 'null');
        
        this.initializeEventListeners();
        this.checkAuthStatus();
    }
    
    initializeEventListeners() {
        // Form submissions
        document.getElementById('loginForm').addEventListener('submit', (e) => this.handleLogin(e));
        document.getElementById('signupForm').addEventListener('submit', (e) => this.handleSignup(e));
        
        // Form switching
        document.getElementById('showSignup').addEventListener('click', (e) => this.showSignupForm(e));
        document.getElementById('showLogin').addEventListener('click', (e) => this.showLoginForm(e));
    }
    
    checkAuthStatus() {
        if (this.token && this.user) {
            // User is already authenticated, redirect to main app
            window.location.href = '/';
        }
    }
    
    showSignupForm(e) {
        e.preventDefault();
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('signup-form').classList.remove('hidden');
        this.clearStatus();
    }
    
    showLoginForm(e) {
        e.preventDefault();
        document.getElementById('signup-form').classList.add('hidden');
        document.getElementById('login-form').classList.remove('hidden');
        this.clearStatus();
    }
    
    async handleLogin(e) {
        e.preventDefault();
        
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;
        
        console.log('Login attempt:', { username, password: '***' });
        
        if (!username || !password) {
            this.showStatus('Please fill in all fields', 'error');
            return;
        }
        
        try {
            console.log('Making login request to:', `${this.apiBaseUrl}/auth/login`);
            const response = await fetch(`${this.apiBaseUrl}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });
            
            console.log('Login response status:', response.status);
            const data = await response.json();
            console.log('Login response data:', data);
            
            if (response.ok) {
                this.setAuthData(data.token, data.user);
                this.showStatus('Login successful! Redirecting...', 'success');
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                this.showStatus(data.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showStatus('Network error. Please try again.', 'error');
        }
    }
    
    async handleSignup(e) {
        e.preventDefault();
        
        const username = document.getElementById('signupUsername').value;
        const email = document.getElementById('signupEmail').value;
        const password = document.getElementById('signupPassword').value;
        
        console.log('Signup attempt:', { username, email, password: '***' });
        
        if (!username || !email || !password) {
            this.showStatus('Please fill in all fields', 'error');
            return;
        }
        
        if (password.length < 6) {
            this.showStatus('Password must be at least 6 characters', 'error');
            return;
        }
        
        try {
            console.log('Making signup request to:', `${this.apiBaseUrl}/auth/signup`);
            const response = await fetch(`${this.apiBaseUrl}/auth/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, email, password })
            });
            
            console.log('Signup response status:', response.status);
            const data = await response.json();
            console.log('Signup response data:', data);
            
            if (response.ok) {
                this.setAuthData(data.token, data.user);
                this.showStatus('Account created successfully! Redirecting...', 'success');
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                this.showStatus(data.error || 'Signup failed', 'error');
            }
        } catch (error) {
            console.error('Signup error:', error);
            this.showStatus('Network error. Please try again.', 'error');
        }
    }
    
    setAuthData(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('sprout_token', token);
        localStorage.setItem('sprout_user', JSON.stringify(user));
    }
    
    showStatus(message, type = 'info') {
        const statusEl = document.getElementById('authStatus');
        statusEl.textContent = message;
        statusEl.className = `auth-status ${type}`;
        statusEl.style.display = 'block';
    }
    
    clearStatus() {
        const statusEl = document.getElementById('authStatus');
        statusEl.style.display = 'none';
        statusEl.textContent = '';
    }
}

// Initialize authentication manager
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
}); 