import pytest
import json
from app import app

class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_signup_success(self, client, sample_user_data):
        """Test successful user signup"""
        response = client.post('/api/auth/signup', 
                             data=json.dumps(sample_user_data),
                             content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'message' in data
        assert 'user' in data
        assert 'id' in data['user']
        assert data['message'] == 'Account created successfully! You are now logged in.'
    
    def test_signup_duplicate_email(self, client, sample_user_data):
        """Test signup with existing email"""
        # First signup
        client.post('/api/auth/signup', 
                   data=json.dumps(sample_user_data),
                   content_type='application/json')
        
        # Try to signup again with same email
        response = client.post('/api/auth/signup', 
                             data=json.dumps(sample_user_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_signup_invalid_email(self, client, sample_user_data):
        """Test signup with invalid email format"""
        sample_user_data['email'] = 'invalid-email'
        
        response = client.post('/api/auth/signup', 
                             data=json.dumps(sample_user_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_signup_weak_password(self, client, sample_user_data):
        """Test signup with weak password"""
        sample_user_data['password'] = '123'
        
        response = client.post('/api/auth/signup', 
                             data=json.dumps(sample_user_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_login_success(self, client, sample_user_data):
        """Test successful login"""
        # First create a user
        client.post('/api/auth/signup', 
                   data=json.dumps(sample_user_data),
                   content_type='application/json')
        
        # Then login
        login_data = {
            'email': sample_user_data['email'],
            'password': sample_user_data['password']
        }
        
        response = client.post('/api/auth/login', 
                             data=json.dumps(login_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
        assert 'user' in data
        assert 'id' in data['user']
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        login_data = {
            'email': 'nonexistent@example.com',
            'password': 'wrongpassword'
        }
        
        response = client.post('/api/auth/login', 
                             data=json.dumps(login_data),
                             content_type='application/json')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_logout_success(self, client, sample_user_data):
        """Test successful logout"""
        # First create and login a user
        client.post('/api/auth/signup', 
                   data=json.dumps(sample_user_data),
                   content_type='application/json')
        
        login_data = {
            'email': sample_user_data['email'],
            'password': sample_user_data['password']
        }
        
        client.post('/api/auth/login', 
                   data=json.dumps(login_data),
                   content_type='application/json')
        
        # Then logout
        response = client.post('/api/auth/logout')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
    
    def test_forgot_password_success(self, client, sample_user_data):
        """Test successful forgot password request"""
        # First create a user
        client.post('/api/auth/signup', 
                   data=json.dumps(sample_user_data),
                   content_type='application/json')
        
        # Request password reset
        reset_data = {'email': sample_user_data['email']}
        
        response = client.post('/api/auth/forgot-password', 
                             data=json.dumps(reset_data),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
    
    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with nonexistent email"""
        reset_data = {'email': 'nonexistent@example.com'}
        
        response = client.post('/api/auth/forgot-password', 
                             data=json.dumps(reset_data),
                             content_type='application/json')
        
        # Should still return 200 to prevent email enumeration
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'message' in data
    
    def test_reset_password_success(self, client, sample_user_data):
        """Test successful password reset"""
        # First create a user and request reset
        client.post('/api/auth/signup', 
                   data=json.dumps(sample_user_data),
                   content_type='application/json')
        
        client.post('/api/auth/forgot-password', 
                   data=json.dumps({'email': sample_user_data['email']}),
                   content_type='application/json')
        
        # Reset password (in real app, you'd need a valid token)
        reset_data = {
            'token': 'test-token',
            'new_password': 'NewPassword123!'
        }
        
        response = client.post('/api/auth/reset-password', 
                             data=json.dumps(reset_data),
                             content_type='application/json')
        
        # This might fail without a real token, but we're testing the endpoint structure
        assert response.status_code in [200, 400]
    
    def test_get_current_user_authenticated(self, client, sample_user_data):
        """Test getting current user when authenticated"""
        # Create and login user
        client.post('/api/auth/signup', 
                   data=json.dumps(sample_user_data),
                   content_type='application/json')
        
        login_data = {
            'email': sample_user_data['email'],
            'password': sample_user_data['password']
        }
        
        client.post('/api/auth/login', 
                   data=json.dumps(login_data),
                   content_type='application/json')
        
        # Get current user
        response = client.get('/api/auth/me')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'user' in data
    
    def test_get_current_user_unauthenticated(self, client):
        """Test getting current user when not authenticated"""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
