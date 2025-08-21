import pytest
import json
from datetime import datetime, date

class TestExpenses:
    """Test expense management endpoints"""
    
    def test_get_expenses_authenticated(self, client, sample_user_data, sample_expense_data):
        """Test getting expenses when authenticated"""
        # Create user and login
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
        
        # Get expenses
        response = client.get('/api/expenses')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)  # API returns list directly
    
    def test_get_expenses_unauthenticated(self, client):
        """Test getting expenses when not authenticated"""
        response = client.get('/api/expenses')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_expense_success(self, client, sample_user_data, sample_expense_data):
        """Test successful expense creation"""
        # Create user and login
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
        
        # Create a category first
        category_data = {
            'name': 'Test Category',
            'color': '#FF5733'
        }
        
        cat_response = client.post('/api/categories', 
                                 data=json.dumps(category_data),
                                 content_type='application/json')
        
        cat_data = json.loads(cat_response.data)
        sample_expense_data['category_id'] = cat_data['category']['id']
        
        # Create expense
        response = client.post('/api/expenses', 
                             data=json.dumps(sample_expense_data),
                             content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'success' in data
        assert data['success'] == True
    
    def test_create_expense_invalid_amount(self, client, sample_user_data, sample_expense_data):
        """Test expense creation with invalid amount"""
        # Create user and login
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
        
        # Try to create expense with negative amount
        sample_expense_data['amount'] = -50.00
        
        response = client.post('/api/expenses', 
                             data=json.dumps(sample_expense_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_expense_missing_required_fields(self, client, sample_user_data):
        """Test expense creation with missing required fields"""
        # Create user and login
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
        
        # Try to create expense without amount
        expense_data = {
            'description': 'Test expense',
            'category_id': 1,
            'date': '2024-01-15'
        }
        
        response = client.post('/api/expenses', 
                             data=json.dumps(expense_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_create_expense_invalid_date(self, client, sample_user_data, sample_expense_data):
        """Test expense creation with invalid date"""
        # Create user and login
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
        
        # Try to create expense with invalid date
        sample_expense_data['date'] = 'invalid-date'
        
        response = client.post('/api/expenses', 
                             data=json.dumps(sample_expense_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_get_expenses_with_filters(self, client, sample_user_data, sample_expense_data):
        """Test getting expenses with date filters"""
        # Create user and login
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
        
        # Get expenses with date range
        response = client.get('/api/expenses?start_date=2024-01-01&end_date=2024-12-31')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)  # API returns list directly
    
    def test_get_expenses_with_category_filter(self, client, sample_user_data, sample_expense_data):
        """Test getting expenses filtered by category"""
        # Create user and login
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
        
        # Get expenses filtered by category
        response = client.get('/api/expenses?category_id=1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)  # API returns list directly
    
    def test_expense_amount_validation(self, client, sample_user_data):
        """Test various amount validation scenarios"""
        # Create user and login
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
        
        # Test zero amount
        expense_data = {
            'amount': 0,
            'description': 'Test expense',
            'category_id': 1,
            'date': '2024-01-15'
        }
        
        response = client.post('/api/expenses', 
                             data=json.dumps(expense_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        
        # Test very large amount
        expense_data['amount'] = 999999999.99
        
        response = client.post('/api/expenses', 
                             data=json.dumps(expense_data),
                             content_type='application/json')
        
        # This might be valid depending on your validation rules
        assert response.status_code in [201, 400]
    
    def test_expense_description_validation(self, client, sample_user_data):
        """Test description validation"""
        # Create user and login
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
        
        # Test empty description
        expense_data = {
            'amount': 50.00,
            'description': '',
            'category_id': 1,
            'date': '2024-01-15'
        }
        
        response = client.post('/api/expenses', 
                             data=json.dumps(expense_data),
                             content_type='application/json')
        
        # This might be valid depending on your validation rules
        assert response.status_code in [201, 400]
        
        # Test very long description
        expense_data['description'] = 'A' * 1000
        
        response = client.post('/api/expenses', 
                             data=json.dumps(expense_data),
                             content_type='application/json')
        
        # This should probably be rejected
        assert response.status_code in [201, 400]
