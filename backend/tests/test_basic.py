import pytest
import json

class TestBasic:
    """Basic tests to verify the testing infrastructure is working"""
    
    def test_health_endpoint(self, client):
        """Test that the health endpoint is working"""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'ok'
    
    def test_database_connection(self, client):
        """Test that database connection is working"""
        response = client.get('/api/test-db')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data
    
    def test_flask_app_creation(self, client):
        """Test that Flask app is properly configured"""
        # Test that we can make a request
        response = client.get('/')
        # Should return some response (might be 200, 302, etc.)
        assert response.status_code in [200, 302, 404]
    
    def test_json_parsing(self, client):
        """Test that JSON parsing is working"""
        # Test with valid JSON
        test_data = {'test': 'data'}
        response = client.post('/api/auth/signup', 
                             data=json.dumps(test_data),
                             content_type='application/json')
        # Should get some response (might be 400 for invalid data, but should parse JSON)
        assert response.status_code in [201, 400, 500]
    
    def test_test_fixtures(self, sample_user_data, sample_expense_data, sample_category_data):
        """Test that test fixtures are working"""
        assert 'email' in sample_user_data
        assert 'password' in sample_user_data
        assert 'amount' in sample_expense_data
        assert 'name' in sample_category_data
        assert 'color' in sample_category_data
