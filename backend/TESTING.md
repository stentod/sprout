# Testing Guide for Sprout Application

This guide explains how to use the comprehensive testing infrastructure we've set up for your Sprout budget tracking application.

## 🎯 Why Testing Matters

Testing will make your app better by:

1. **Catching Bugs Early** - Find issues during development, not when users report them
2. **Confidence to Make Changes** - Refactor code without worrying about breaking existing features
3. **Living Documentation** - Tests show how your code should behave
4. **Better Code Design** - Writing tests forces you to think about how code will be used
5. **Regression Prevention** - Ensure fixed bugs never come back

## 🚀 Quick Start

### Install Testing Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Run All Tests

```bash
# Using the test runner script
python run_tests.py

# Or directly with pytest
python -m pytest
```

### Run Specific Test Types

```bash
# Authentication tests only
python run_tests.py --type auth

# Expense management tests only
python run_tests.py --type expenses

# Category management tests only
python run_tests.py --type categories

# User preferences tests only
python run_tests.py --type preferences

# Summary/reporting tests only
python run_tests.py --type summary
```

## 📊 Test Coverage

Generate a coverage report to see how much of your code is tested:

```bash
# Run tests with coverage
python run_tests.py --coverage

# Or directly
python -m pytest --cov=app --cov-report=html:htmlcov
```

This will create an HTML coverage report in the `htmlcov/` directory. Open `htmlcov/index.html` in your browser to see detailed coverage information.

## 🧪 Test Structure

### Test Files

- `tests/test_auth.py` - Authentication (signup, login, logout, password reset)
- `tests/test_expenses.py` - Expense management (create, read, validate)
- `tests/test_categories.py` - Category management (create, update, delete, budget tracking)
- `tests/test_preferences.py` - User preferences (daily limits, category requirements)
- `tests/test_summary.py` - Summary and reporting (financial summaries, history)

### Test Types

Each test file contains multiple test classes that cover:

1. **Happy Path Tests** - Normal, expected usage
2. **Error Handling Tests** - Invalid inputs, missing data
3. **Edge Case Tests** - Boundary conditions, unusual inputs
4. **Authentication Tests** - Protected vs unprotected endpoints
5. **Validation Tests** - Input validation and business rules

## 🔧 Test Configuration

### conftest.py

This file contains shared test fixtures:

- `client` - Flask test client
- `sample_user_data` - Test user data
- `sample_expense_data` - Test expense data
- `sample_category_data` - Test category data
- `auth_headers` - Authentication headers for protected endpoints

### pytest.ini

Configuration for pytest including:

- Test discovery patterns
- Coverage reporting
- Custom markers for test categorization
- Output formatting

## 🎯 What Each Test Covers

### Authentication Tests (`test_auth.py`)

- ✅ User signup with valid data
- ✅ Duplicate email handling
- ✅ Invalid email format validation
- ✅ Weak password rejection
- ✅ Successful login
- ✅ Invalid credentials handling
- ✅ Logout functionality
- ✅ Password reset flow
- ✅ Session management

### Expense Tests (`test_expenses.py`)

- ✅ Creating expenses with valid data
- ✅ Invalid amount validation (negative, zero, very large)
- ✅ Missing required fields
- ✅ Invalid date formats
- ✅ Date range filtering
- ✅ Category filtering
- ✅ Description validation
- ✅ Authentication requirements

### Category Tests (`test_categories.py`)

- ✅ Creating categories with valid data
- ✅ Missing name validation
- ✅ Invalid color format validation
- ✅ Duplicate name handling
- ✅ Budget limit updates
- ✅ Category deletion
- ✅ Budget tracking
- ✅ Color validation (valid/invalid hex codes)

### Preferences Tests (`test_preferences.py`)

- ✅ Daily limit setting and retrieval
- ✅ Invalid daily limit validation
- ✅ Category requirement toggles
- ✅ Preference persistence across sessions
- ✅ Edge case validation
- ✅ Data type validation

### Summary Tests (`test_summary.py`)

- ✅ Financial summary calculations
- ✅ Expense history retrieval
- ✅ Date range filtering
- ✅ Pagination
- ✅ Category filtering
- ✅ Calculation accuracy verification
- ✅ Empty data handling

## 🚨 Common Test Scenarios

### Testing Protected Endpoints

```python
def test_protected_endpoint_authenticated(self, client, sample_user_data):
    # Create user and login
    client.post('/api/auth/signup', data=json.dumps(sample_user_data))
    client.post('/api/auth/login', data=json.dumps(login_data))
    
    # Now test the protected endpoint
    response = client.get('/api/protected-endpoint')
    assert response.status_code == 200

def test_protected_endpoint_unauthenticated(self, client):
    # Test without authentication
    response = client.get('/api/protected-endpoint')
    assert response.status_code == 401
```

### Testing Data Validation

```python
def test_invalid_input_validation(self, client, sample_user_data):
    # Setup authentication
    client.post('/api/auth/signup', data=json.dumps(sample_user_data))
    
    # Test with invalid data
    invalid_data = {'amount': -50.00}  # Negative amount
    response = client.post('/api/expenses', data=json.dumps(invalid_data))
    
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
```

### Testing Business Logic

```python
def test_business_rule_validation(self, client, sample_user_data):
    # Setup user and create expense
    # ... setup code ...
    
    # Test that business rules are enforced
    response = client.get('/api/summary')
    summary = json.loads(response.data)['summary']
    
    # Verify calculations are correct
    assert summary['total_spent'] == expected_amount
    assert summary['remaining_budget'] == expected_remaining
```

## 🔍 Debugging Failed Tests

### Common Issues

1. **Database Connection Errors**
   - Ensure your test database is set up
   - Check `TEST_DATABASE_URL` environment variable

2. **Authentication Issues**
   - Tests create their own users and sessions
   - Each test should be independent

3. **Timing Issues**
   - Some tests might depend on database state
   - Use proper test isolation

### Debug Commands

```bash
# Run a specific test with verbose output
python -m pytest tests/test_auth.py::TestAuthentication::test_signup_success -v -s

# Run tests and stop on first failure
python -m pytest -x

# Run tests with maximum verbosity
python -m pytest -vvv

# Run tests and show local variables on failure
python -m pytest -l
```

## 📈 Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        run: |
          cd backend
          python -m pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## 🎯 Best Practices

### Writing New Tests

1. **Test One Thing** - Each test should verify one specific behavior
2. **Use Descriptive Names** - Test names should explain what they're testing
3. **Arrange-Act-Assert** - Structure tests with setup, action, verification
4. **Test Edge Cases** - Don't just test happy paths
5. **Keep Tests Independent** - Tests shouldn't depend on each other

### Example Test Structure

```python
def test_feature_behavior(self, client, sample_data):
    """Test description of what this test verifies"""
    # Arrange - Set up test data and conditions
    client.post('/api/auth/signup', data=json.dumps(sample_data))
    
    # Act - Perform the action being tested
    response = client.post('/api/endpoint', data=json.dumps(test_data))
    
    # Assert - Verify the expected outcome
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'expected_field' in data
```

## 🚀 Next Steps

1. **Run the tests** to see what's currently working
2. **Fix any failing tests** - they might reveal real bugs!
3. **Add more tests** for any missing functionality
4. **Set up CI/CD** to run tests automatically
5. **Monitor coverage** and aim for 80%+ coverage

## 📞 Getting Help

If you encounter issues with the tests:

1. Check the test output for specific error messages
2. Verify your database connection and environment variables
3. Look at the test code to understand what it's trying to do
4. Add debug prints or use pytest's `-s` flag to see output

The tests are designed to be self-documenting - reading the test code is often the best way to understand how your application should behave!
