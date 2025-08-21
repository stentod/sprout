import pytest
import os
import tempfile
import psycopg2
import psycopg2.extras
from app import app, get_db_connection
from dotenv import load_dotenv

# Load test environment variables
load_dotenv()

@pytest.fixture
def client():
    """Create a test client for the Flask application"""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    # Use a test database or in-memory database
    app.config['DATABASE_URL'] = os.environ.get('TEST_DATABASE_URL', 'postgresql://test_user:test_pass@localhost:5432/sprout_test')
    
    with app.test_client() as client:
        with app.app_context():
            # Set up test database
            setup_test_database()
            yield client
            # Clean up test database
            cleanup_test_database()

@pytest.fixture
def auth_headers():
    """Create authentication headers for testing authenticated endpoints"""
    def _auth_headers(user_id=None):
        headers = {'Content-Type': 'application/json'}
        if user_id:
            # In a real test, you'd create a session or JWT token
            # For now, we'll use a simple approach
            headers['X-Test-User-ID'] = str(user_id)
        return headers
    return _auth_headers

@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        'email': 'test@example.com',
        'password': 'TestPassword123!',
        'first_name': 'Test',
        'last_name': 'User'
    }

@pytest.fixture
def sample_expense_data():
    """Sample expense data for testing"""
    return {
        'amount': 50.00,
        'description': 'Test expense',
        'category_id': 1,
        'date': '2024-01-15'
    }

@pytest.fixture
def sample_category_data():
    """Sample category data for testing"""
    return {
        'name': 'Test Category',
        'color': '#FF5733',
        'budget_limit': 100.00
    }

def setup_test_database():
    """Set up test database - just clean existing data"""
    cleanup_test_database()

def cleanup_test_database():
    """Clean up test database after tests"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Clear all test data from real tables
        cur.execute("DELETE FROM expenses")
        cur.execute("DELETE FROM categories")
        cur.execute("DELETE FROM users")
        
        # Reset sequences if they exist
        try:
            cur.execute("ALTER SEQUENCE users_id_seq RESTART WITH 1")
            cur.execute("ALTER SEQUENCE categories_id_seq RESTART WITH 1")
            cur.execute("ALTER SEQUENCE expenses_id_seq RESTART WITH 1")
        except:
            pass  # Sequences might not exist or might be named differently
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"Error cleaning up test database: {e}")

@pytest.fixture
def mock_db_connection(monkeypatch):
    """Mock database connection for unit tests"""
    class MockConnection:
        def cursor(self):
            return MockCursor()
        
        def commit(self):
            pass
        
        def close(self):
            pass
    
    class MockCursor:
        def execute(self, query, params=None):
            pass
        
        def fetchall(self):
            return []
        
        def fetchone(self):
            return None
        
        def close(self):
            pass
    
    def mock_get_db_connection():
        return MockConnection()
    
    monkeypatch.setattr('app.get_db_connection', mock_get_db_connection)
