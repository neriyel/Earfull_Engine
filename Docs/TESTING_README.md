# Authentication Testing Guide

## Overview

This project contains comprehensive end-to-end (E2E) tests for JWT-based authentication flows. The tests validate user registration, login, token management, and protected resource access.

**Test Files:**
- `tests/e2e/test_auth_flow.py` - Synchronous API tests (httpx)
- `tests/e2e/test_auth_flow_playwright.py` - Asynchronous tests (Playwright)

**Documentation:**
- `AUTHENTICATION_TEST_INTERVIEW_GUIDE.md` - Complete interview preparation guide

---

## Quick Start

### 1. Install Dependencies

```bash
# Activate virtual environment
source EE_venv/Scripts/activate  # Windows PowerShell: .\EE_venv\Scripts\Activate.ps1

# Install required packages
pip install -r requirements.txt

# Install Playwright browsers (first time only)
playwright install
```

### 2. Configure Database

```bash
# Apply migrations
cd earfull_engine
python manage.py migrate

# (Optional) Create test user manually
python manage.py createsuperuser
```

### 3. Start Django Server

In one terminal:
```bash
cd earfull_engine
python manage.py runserver
```

The server will start at `http://localhost:8000`

### 4. Run Tests

In another terminal (with venv activated):

```bash
# Run all authentication tests
pytest earfull_engine/tests/e2e/ -v

# Run only synchronous tests
pytest earfull_engine/tests/e2e/test_auth_flow.py -v

# Run only async/Playwright tests
pytest earfull_engine/tests/e2e/test_auth_flow_playwright.py -v

# Run specific test class
pytest earfull_engine/tests/e2e/test_auth_flow.py::TestUserRegistration -v

# Run specific test
pytest earfull_engine/tests/e2e/test_auth_flow.py::TestUserRegistration::test_successful_registration -v

# Run with detailed output
pytest earfull_engine/tests/e2e/ -vv

# Run with print statements visible
pytest earfull_engine/tests/e2e/ -s

# Run with coverage report
pytest earfull_engine/tests/e2e/ --cov=earfull_engine.accounts --cov-report=html
coverage report
```

---

## Test Structure

### Test Organization

```
tests/
├── api/                              # API tests
│   └── test_accounts_api.py         # Account endpoint tests
├── e2e/                             # End-to-end tests
│   ├── test_auth_flow.py            # Synchronous auth tests
│   └── test_auth_flow_playwright.py # Async Playwright tests
└── unit/
    └── test_services.py             # Unit tests
```

### Test Classes

**test_auth_flow.py (Synchronous - httpx):**
- `TestUserRegistration` - Registration endpoint tests
- `TestUserLogin` - Login and token generation tests
- `TestTokenRefresh` - Token refresh functionality
- `TestAuthenticatedRequests` - Protected endpoint access
- `TestEndToEndAuthFlow` - Complete user journey

**test_auth_flow_playwright.py (Asynchronous - Playwright):**
- `TestPlaywrightAuthFlow` - Advanced auth scenarios with Playwright
- `TestParametrizedAuthScenarios` - Parametrized test cases
- Concurrent user testing
- Token security testing

---

## Authentication Flows Tested

### 1. User Registration

**Endpoint:** `POST /register/`

**What's Tested:**
- ✓ Successful registration with valid credentials
- ✗ Duplicate username prevention
- ✗ Duplicate email prevention
- ✗ Missing required fields
- ✗ Invalid input validation

**Example Test:**
```python
def test_successful_registration(http_client, unique_user_data):
    response = http_client.post(
        f"{BASE_URL}/register/",
        json={
            "username": unique_user_data["username"],
            "email": unique_user_data["email"],
            "password": unique_user_data["password"]
        }
    )
    assert response.status_code == 201
    assert response.json()["username"] == unique_user_data["username"]
    assert "password" not in response.json()  # Security check
```

### 2. User Login (Token Generation)

**Endpoint:** `POST /login/`

**What's Tested:**
- ✓ Successful login returns access & refresh tokens
- ✗ User not found returns 401
- ✗ Wrong password returns 401
- ✗ Missing credentials returns 400

**Example Test:**
```python
def test_successful_login(http_client, registered_user):
    response = http_client.post(
        f"{BASE_URL}/login/",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"]
        }
    )
    assert response.status_code == 200
    tokens = response.json()
    assert "access" in tokens
    assert "refresh" in tokens
```

### 3. Protected Resource Access

**Endpoint:** `GET /me/`

**What's Tested:**
- ✓ Valid token grants access
- ✗ Missing token returns 401
- ✗ Invalid token returns 401
- ✗ Malformed authorization header returns 401

**Example Test:**
```python
def test_get_user_info_with_valid_token(http_client, registered_user):
    # Get token from login
    login_response = http_client.post(...)
    access_token = login_response.json()["access"]
    
    # Use token to access protected endpoint
    response = http_client.get(
        f"{BASE_URL}/me/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == registered_user["email"]
```

### 4. Token Refresh

**Endpoint:** `POST /refresh/`

**What's Tested:**
- ✓ Valid refresh token returns new access token
- ✗ Invalid refresh token returns 401
- ✗ Missing token returns 400

**Example Test:**
```python
def test_successful_token_refresh(http_client, registered_user):
    # Get tokens from login
    login_response = http_client.post(...)
    refresh_token = login_response.json()["refresh"]
    
    # Refresh token
    response = http_client.post(
        f"{BASE_URL}/refresh/",
        json={"refresh": refresh_token}
    )
    assert response.status_code == 200
    assert "access" in response.json()
```

---

## Key Testing Concepts Demonstrated

### 1. **Fixtures** (Pytest)
Reusable setup code that provides test data and configurations:

```python
@pytest.fixture
def http_client():
    """Provides HTTP client for each test"""
    client = httpx.Client()
    yield client
    client.close()

@pytest.fixture
def unique_user_data():
    """Generates unique credentials to prevent test conflicts"""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"testuser_{unique_id}@test.com",
        "password": "SecurePassword123!"
    }
```

**Benefits:**
- No code duplication
- Automatic setup/teardown
- Tests are independent

### 2. **AAA Pattern** (Arrange-Act-Assert)
Clear test structure:

```python
def test_something(http_client):
    # ARRANGE - Set up test data
    user_data = {"username": "test", ...}
    
    # ACT - Execute the action
    response = http_client.post("/register/", json=user_data)
    
    # ASSERT - Verify results
    assert response.status_code == 201
```

### 3. **Negative Testing**
Testing error paths and invalid inputs:

```python
def test_login_with_wrong_password(http_client, registered_user):
    response = http_client.post(
        "/login/",
        json={
            "username": registered_user["username"],
            "password": "WrongPassword"
        }
    )
    assert response.status_code == 401  # Should reject
```

### 4. **Security Testing**
Validating authentication and authorization:

```python
def test_protected_endpoint_without_token(http_client):
    """Verify unauthenticated requests are rejected"""
    response = http_client.get("/me/")
    assert response.status_code == 401

def test_password_not_in_response(http_client):
    """Verify password never exposed"""
    response = http_client.get("/me/", headers={"Authorization": f"Bearer {token}"})
    assert "password" not in response.json()
```

### 5. **Parametrized Testing**
Test multiple scenarios with same logic:

```python
@pytest.mark.parametrize("password", [
    "ValidPassword123!",
    "Another@Pass2024",
    "Complex!P@ss0rd",
])
def test_login_with_various_passwords(http_client, password):
    # Test runs 3 times with different passwords
    ...
```

### 6. **Asynchronous Testing**
Modern async/await patterns with Playwright:

```python
@pytest.mark.asyncio
async def test_concurrent_logins(playwright_context):
    # Test multiple users logging in simultaneously
    tasks = [login_user(context, user) for user in users]
    tokens = await asyncio.gather(*tasks)
    assert len(set(tokens)) == 3  # All unique
```

---

## Understanding Test Output

### Successful Run
```
test_auth_flow.py::TestUserRegistration::test_successful_registration PASSED
test_auth_flow.py::TestUserRegistration::test_registration_with_duplicate_username PASSED
test_auth_flow.py::TestUserLogin::test_successful_login PASSED
...
====== 15 passed in 2.34s ======
```

### Failed Test
```
test_auth_flow.py::TestUserLogin::test_successful_login FAILED
AssertionError: assert 200 == 201
    expected: 201
    actual: 200
```

### Coverage Report
```bash
pytest --cov=earfull_engine.accounts --cov-report=html

# Opens coverage/index.html with visual report
```

---

## Common Issues & Solutions

### Issue: "Connection refused" error
**Cause:** Django server not running
**Solution:** Start Django in another terminal: `python manage.py runserver`

### Issue: "ModuleNotFoundError: No module named 'httpx'"
**Cause:** Dependencies not installed
**Solution:** `pip install -r requirements.txt`

### Issue: "Playwright browser not found"
**Cause:** Browsers not installed
**Solution:** `playwright install`

### Issue: "Tests fail with database errors"
**Cause:** Migrations not applied
**Solution:** `python manage.py migrate`

### Issue: Tests pass locally but fail in deployment
**Cause:** Base URL hardcoded for localhost
**Solution:** Use environment variables for BASE_URL

---

## Interview Preparation

### Key Points to Discuss
- Why each test exists
- What authentication concepts are tested
- How fixture system reduces duplication
- Why security testing is important
- How to organize tests at scale
- Testing best practices applied

### Know These Concepts
- JWT tokens and how they work
- Access vs. Refresh tokens
- Authentication vs. Authorization
- API status code meanings (200, 201, 400, 401, 403, 500)
- AAA testing pattern
- Pytest fixtures and marks

### Be Ready to Explain
- Registration flow: username/email validation, password hashing
- Login flow: credential validation, token generation
- Protected endpoint: token verification, claims validation
- Token refresh: token validation, new token issuance

See `AUTHENTICATION_TEST_INTERVIEW_GUIDE.md` for comprehensive interview prep.

---

## Extending the Tests

### Add More Test Scenarios

**Password Reset Flow:**
```python
class TestPasswordReset:
    def test_request_password_reset(self, http_client):
        """User requests password reset link"""
        response = http_client.post(
            "/password-reset/request/",
            json={"email": "user@example.com"}
        )
        assert response.status_code == 200
```

**Email Verification:**
```python
class TestEmailVerification:
    def test_verify_email(self, http_client):
        """User verifies their email"""
        response = http_client.post(
            "/verify-email/",
            json={"token": verification_token}
        )
        assert response.status_code == 200
```

**Two-Factor Authentication:**
```python
class TestTwoFactor:
    def test_2fa_code_required(self, http_client, registered_user):
        """After login, 2FA code is required"""
        response = http_client.post("/login/", json=credentials)
        assert response.status_code == 202  # Accepted, pending 2FA
```

---

## Running Tests in CI/CD

### GitHub Actions Example

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.13'
      - run: pip install -r requirements.txt
      - run: playwright install
      - run: python manage.py migrate
      - run: pytest earfull_engine/tests/e2e/ -v --cov
```

---

## Resources

**Testing Documentation:**
- Pytest: https://docs.pytest.org/
- Playwright: https://playwright.dev/python/
- Testing Best Practices: https://testingtranslator.com/

**Authentication:**
- JWT.io: https://jwt.io/
- Django REST JWT: https://django-rest-framework-simplejwt.readthedocs.io/

---

## Questions?

Refer to `AUTHENTICATION_TEST_INTERVIEW_GUIDE.md` for detailed explanations of testing concepts and interview preparation.

Good luck with your interview! 🚀
