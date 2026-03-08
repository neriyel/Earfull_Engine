"""
Authentication Flow End-to-End Tests
====================================

Purpose:
    This test suite validates the complete authentication workflow of the Earfull Engine API,
    including user registration, login, token refresh, and authenticated requests.

Test Scope:
    - User registration with validation
    - JWT token generation during login
    - Token refresh functionality
    - Authenticated API access (GET /me/)
    - Error handling and edge cases
    - Input validation and security checks

Testing Concepts Demonstrated:
    1. Test Fixtures: Reusable test data and setup (users, endpoints)
    2. Test Organization: Grouped by feature (registration, login, etc.)
    3. AAA Pattern: Arrange (setup), Act (execute), Assert (verify)
    4. Negative Testing: Testing error paths and invalid inputs
    5. API Testing: Direct HTTP requests to JWT endpoints

Dependencies:
    - pytest: Test framework
    - pytest-asyncio: Async test support
    - httpx: HTTP client for API testing (Playwright doesn't need browser for API tests)

Notes:
    These tests follow best practices for API testing:
    - Each test is independent and doesn't rely on other tests
    - Test data is generated fresh for each test
    - Tests verify both happy paths and error scenarios
    - Response codes and error messages are validated
"""

import pytest
import httpx
import json
from typing import Dict, Tuple
import uuid
import asyncio


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

BASE_URL = "http://127.0.0.1:8000/accounts"
API_VERSION = "v1"

# API Endpoints
ENDPOINTS = {
    "register": f"{BASE_URL}/register/",
    "login": f"{BASE_URL}/login/",
    "refresh": f"{BASE_URL}/refresh/",
    "me": f"{BASE_URL}/me/",
}

# Test data templates
VALID_USER_DATA = {
    "username": None,  # Will be generated per test
    "email": None,  # Will be generated per test
    "password": "SecurePassword123!",
}


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def http_client() -> httpx.Client:
    """
    Fixture: HTTP Client

    Purpose: Provides a reusable HTTP client for making API requests.

    Why fixtures are useful:
    - Setup and teardown is automatic
    - Can be reused across multiple tests
    - Keeps tests clean and DRY (Don't Repeat Yourself)

    Yields:
        httpx.Client: Synchronous HTTP client for API testing
    """
    client = httpx.Client(timeout=30.0)
    yield client  # Yield allows for cleanup after (give client -> run test -> run cleanup code below)
    client.close()


@pytest.fixture
def unique_user_data() -> Dict[str, str]:
    """
    Fixture: Unique User Data Generator

    Purpose: Generates unique test credentials for each test run.

    Why unique data matters:
    - Prevents test failures due to duplicate records
    - Tests run sequentially without interfering with each other
    - Critical for integration tests that hit a real database

    Returns:
        dict: Contains username, email, and password

    Example:
        {
            "username": "testuser_a1b2c3d4",
            "email": "testuser_a1b2c3d4@test.com",
            "password": "SecurePassword123!"
        }
    """
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"testuser_{unique_id}@test.com",
        "password": "SecurePassword123!",
    }


@pytest.fixture
def registered_user(
    http_client: httpx.Client, unique_user_data: Dict[str, str]
) -> Dict[str, str]:
    """
    Fixture: Pre-registered User for Testing

    Purpose: Creates a user account before tests that need an existing user.

    Test Dependencies:
    - Some tests need an existing user (e.g., login tests)
    - Rather than duplicate registration code, we create a fixture
    - This follows the DRY principle

    Args:
        http_client: HTTP client from fixture
        unique_user_data: User credentials from fixture

    Returns:
        dict: The registered user's credentials

    Raises:
        Exception: If registration fails
    """
    response = http_client.post(
        ENDPOINTS["register"],
        json={
            "username": unique_user_data["username"],
            "email": unique_user_data["email"],
            "password": unique_user_data["password"],
        },
    )

    if response.status_code != 201:
        raise Exception(f"Failed to register test user: {response.text}")

    return unique_user_data


# ============================================================================
# TEST SUITE: USER REGISTRATION
# ============================================================================


class TestUserRegistration:
    """
    Test Suite: User Registration

    Scope:
        Tests for the POST /register/ endpoint

    User Stories:
        1. As a new user, I want to create an account with username, email, and password
        2. As the system, I need to prevent duplicate usernames
        3. As the system, I need to prevent duplicate emails
        4. As the system, I need to validate input data
    """

    def test_successful_registration(
        self, http_client: httpx.Client, unique_user_data: Dict[str, str]
    ):
        """
        Test: Successful User Registration (Happy Path)

        Scenario:
            User provides valid, unique credentials

        Expected Behavior:
            - API returns 201 Created
            - Response body contains user data (without password)
            - User can subsequently log in with provided credentials

        Test Technique:
            AAA Pattern (Arrange-Act-Assert):
            - Arrange: Prepare valid user data
            - Act: Send POST request to /register/
            - Assert: Verify status code and response structure
        """
        # Arrange
        user_data = {
            "username": unique_user_data["username"],
            "email": unique_user_data["email"],
            "password": unique_user_data["password"],
        }

        # Act
        response = http_client.post(ENDPOINTS["register"], json=user_data)

        # Assert
        assert (
            response.status_code == 201
        ), f"Expected 201, got {response.status_code}: {response.text}"
        response_data = response.json()
        assert response_data["username"] == unique_user_data["username"]
        assert response_data["email"] == unique_user_data["email"]
        # Security check: password should NEVER be in response
        assert "password" not in response_data

    def test_registration_with_duplicate_username(
        self,
        http_client: httpx.Client,
        registered_user: Dict[str, str],
        unique_user_data: Dict[str, str],
    ):
        """
        Test: Prevent Duplicate Username Registration

        Scenario:
            User tries to register with a username that already exists

        Expected Behavior:
            - API returns 400 Bad Request
            - Error message indicates username is taken
            - No duplicate user is created

        Test Technique:
            Negative Testing: Validating error handling
            - Important for security and data integrity
            - Ensures validation logic works correctly
        """
        # Arrange
        duplicate_user_data = {
            "username": registered_user["username"],  # Use existing username
            "email": unique_user_data["email"],  # New email
            "password": unique_user_data["password"],
        }

        # Act
        response = http_client.post(ENDPOINTS["register"], json=duplicate_user_data)

        # Assert
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        response_data = response.json()
        assert "username" in response_data, "Error should mention 'username' field"

    def test_registration_with_duplicate_email(
        self,
        http_client: httpx.Client,
        registered_user: Dict[str, str],
        unique_user_data: Dict[str, str],
    ):
        """
        Test: Prevent Duplicate Email Registration

        Scenario:
            User tries to register with an email that already exists

        Expected Behavior:
            - API returns 400 Bad Request
            - Error message indicates email is taken
            - No duplicate user is created

        Test Strategy:
            Tests data uniqueness constraint validation
        """
        # Arrange
        duplicate_user_data = {
            "username": unique_user_data["username"],  # New username
            "email": registered_user["email"],  # Use existing email
            "password": unique_user_data["password"],
        }

        # Act
        response = http_client.post(ENDPOINTS["register"], json=duplicate_user_data)

        # Assert
        assert response.status_code == 400
        response_data = response.json()
        assert "email" in response_data

    def test_registration_with_missing_fields(self, http_client: httpx.Client):
        """
        Test: Validate Required Fields

        Scenario:
            User omits required fields from registration

        Expected Behavior:
            - API returns 400 Bad Request
            - Error indicates which fields are required

        Test Coverage:
            Input validation - Essential for API security
        """
        # Arrange
        incomplete_data = {
            "username": "testuser",
            # Missing: email, password
        }

        # Act
        response = http_client.post(ENDPOINTS["register"], json=incomplete_data)

        # Assert
        assert response.status_code == 400
        response_data = response.json()
        # Should have error for missing fields
        assert len(response_data) > 0

    def test_registration_with_weak_password(
        self, http_client: httpx.Client, unique_user_data: Dict[str, str]
    ):
        """
        Test: Password Validation (Extensible Test)

        Scenario:
            User tries to register with a weak password

        Expected Behavior:
            - API should reject weak passwords
            - Error message explains password requirements

        Note:
            This test is conditional - only validates if password rules are implemented.
            Common password requirements:
            - Minimum length (usually 8+ characters)
            - Mix of uppercase/lowercase
            - Includes numbers or special characters
        """
        # Arrange
        weak_password_data = {
            "username": unique_user_data["username"],
            "email": unique_user_data["email"],
            "password": "weak",  # Too short, no special chars
        }

        # Act
        response = http_client.post(ENDPOINTS["register"], json=weak_password_data)

        # Assert - Uncomment if password validation is implemented
        # assert response.status_code == 400
        # Note: If this test fails, consider implementing password validation


# ============================================================================
# TEST SUITE: USER LOGIN & TOKEN GENERATION
# ============================================================================


class TestUserLogin:
    """
    Test Suite: User Login / Token Generation

    Scope:
        Tests for the POST /login/ endpoint

    JWT Authentication Concept:
        - User provides credentials (username, password)
        - Server validates and issues JWT tokens
        - Access Token: Short-lived token for API requests
        - Refresh Token: Long-lived token for getting new access tokens

    Security Consideration:
        JWT tokens contain encoded user information but should be treated as secrets
        - Always sent over HTTPS in production
        - Stored securely on client side
    """

    def test_successful_login(
        self, http_client: httpx.Client, registered_user: Dict[str, str]
    ):
        """
        Test: Successful Login (Happy Path)

        Scenario:
            Registered user logs in with correct credentials

        Expected Behavior:
            - API returns 200 OK
            - Response contains 'access' and 'refresh' tokens
            - Tokens are non-empty strings

        API Testing Concept:
            Verification of response structure and token format
        """
        # Arrange
        login_credentials = {
            "username": registered_user["username"],
            "password": registered_user["password"],
        }

        # Act
        response = http_client.post(ENDPOINTS["login"], json=login_credentials)

        # Assert
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}: {response.text}"
        response_data = response.json()
        assert "access" in response_data, "Response should contain 'access' token"
        assert "refresh" in response_data, "Response should contain 'refresh' token"
        assert len(response_data["access"]) > 0
        assert len(response_data["refresh"]) > 0

    def test_login_with_nonexistent_user(self, http_client: httpx.Client):
        """
        Test: Login with Non-existent User

        Scenario:
            User tries to log in with credentials that don't exist

        Expected Behavior:
            - API returns 401 Unauthorized
            - No tokens are issued
            - Error message is generic (doesn't reveal if user exists)

        Security Note:
            Good API design doesn't disclose whether a username exists
            This prevents user enumeration attacks
        """
        # Arrange
        non_existent_credentials = {
            "username": "nonexistent_user_xyz",
            "password": "SomePassword123!",
        }

        # Act
        response = http_client.post(ENDPOINTS["login"], json=non_existent_credentials)

        # Assert
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"

    def test_login_with_wrong_password(
        self, http_client: httpx.Client, registered_user: Dict[str, str]
    ):
        """
        Test: Login with Incorrect Password

        Scenario:
            User provides correct username but wrong password

        Expected Behavior:
            - API returns 401 Unauthorized
            - Account is not compromised
            - No tokens are issued

        Test Type:
            Negative Test / Security Test
        """
        # Arrange
        wrong_credentials = {
            "username": registered_user["username"],
            "password": "WrongPassword123!",
        }

        # Act
        response = http_client.post(ENDPOINTS["login"], json=wrong_credentials)

        # Assert
        assert response.status_code == 401
        response_data = response.json()
        assert "access" not in response_data, "Should not issue token on wrong password"

    def test_login_with_missing_credentials(self, http_client: httpx.Client):
        """
        Test: Login with Missing Credentials

        Scenario:
            User omits username or password field

        Expected Behavior:
            - API returns 400 Bad Request
            - Error message indicates missing fields
        """
        # Arrange
        incomplete_credentials = {
            "username": "someuser"
            # Missing: password
        }

        # Act
        response = http_client.post(ENDPOINTS["login"], json=incomplete_credentials)

        # Assert
        assert response.status_code == 400


# ============================================================================
# TEST SUITE: TOKEN REFRESH
# ============================================================================


class TestTokenRefresh:
    """
    Test Suite: Token Refresh Functionality

    Scope:
        Tests for the POST /refresh/ endpoint

    Token Refresh Concept:
        - Access tokens have short lifespans (security)
        - Instead of re-entering credentials, use refresh token
        - Refresh token generates new access token (and optionally new refresh token)

    Use Case:
        User stays logged in across multiple sessions
        Example: Mobile app automatically refreshes tokens on app launch
    """

    def test_successful_token_refresh(
        self, http_client: httpx.Client, registered_user: Dict[str, str]
    ):
        """
        Test: Successful Token Refresh

        Scenario:
            User has a valid refresh token and requests a new access token

        Expected Behavior:
            - API returns 200 OK
            - New access token is issued
            - Refresh token may be rotated or reused

        Test Strategy:
            1. Login to get tokens
            2. Use refresh token to get new access token
            3. Verify new access token works
        """
        # Arrange
        login_response = http_client.post(
            ENDPOINTS["login"],
            json={
                "username": registered_user["username"],
                "password": registered_user["password"],
            },
        )
        tokens = login_response.json()
        access_token = tokens["access"]
        refresh_token = tokens["refresh"]

        # Act
        response = http_client.post(
            ENDPOINTS["refresh"], json={"refresh": refresh_token}
        )

        # Assert
        assert response.status_code == 200
        new_tokens = response.json()
        assert "access" in new_tokens
        # New access token should be different from old (usually)
        # but both should be valid
        new_access_token = new_tokens["access"]
        assert (
            new_access_token != access_token
        ), "New access token should be different from old"

    def test_refresh_with_invalid_token(self, http_client: httpx.Client):
        """
        Test: Refresh with Invalid Token

        Scenario:
            User provides a malformed or invalid refresh token

        Expected Behavior:
            - API returns 401 Unauthorized
            - No new token is issued
        """
        # Arrange
        invalid_token = "not.a.valid.jwt.token.xyz"

        # Act
        response = http_client.post(
            ENDPOINTS["refresh"], json={"refresh": invalid_token}
        )

        # Assert
        assert response.status_code == 401

    def test_refresh_with_missing_token(self, http_client: httpx.Client):
        """
        Test: Refresh without Token

        Scenario:
            Request to /refresh/ is missing the refresh token

        Expected Behavior:
            - API returns 400 Bad Request
        """
        # Arrange
        no_token_data = {}

        # Act
        response = http_client.post(ENDPOINTS["refresh"], json=no_token_data)

        # Assert
        assert response.status_code == 400


# ============================================================================
# TEST SUITE: AUTHENTICATED REQUESTS (GET /me/)
# ============================================================================


class TestAuthenticatedRequests:
    """
    Test Suite: Authenticated API Access

    Scope:
        Tests for protected endpoints (e.g., GET /me/)

    Authorization Concept:
        - Endpoints marked with @permission_classes([permissions.IsAuthenticated])
        - Require JWT token in Authorization header
        - Request header format: Authorization: Bearer <access_token>

    Test Strategy:
        - Request with valid token (should succeed)
        - Request without token (should fail)
        - Request with invalid/expired token (should fail)
    """

    def test_get_user_info_with_valid_token(
        self, http_client: httpx.Client, registered_user: Dict[str, str]
    ):
        """
        Test: Retrieve User Info with Valid Token

        Scenario:
            Authenticated user requests their profile info

        Expected Behavior:
            - API returns 200 OK
            - Response contains user data (id, email, first_name, last_name)
            - Password is never included in response

        Security Principle:
            Sensitive data (passwords, tokens) should never be exposed to client
        """
        # Arrange
        login_response = http_client.post(
            ENDPOINTS["login"],
            json={
                "username": registered_user["username"],
                "password": registered_user["password"],
            },
        )
        access_token = login_response.json()["access"]

        # Act
        response = http_client.get(
            ENDPOINTS["me"], headers={"Authorization": f"Bearer {access_token}"}
        )

        # Assert
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["email"] == registered_user["email"]
        assert "password" not in user_data
        assert "id" in user_data

    def test_get_user_info_without_token(self, http_client: httpx.Client):
        """
        Test: Retrieve User Info without Authentication

        Scenario:
            Unauthenticated user tries to access protected endpoint

        Expected Behavior:
            - API returns 401 Unauthorized
            - Error message indicates authentication is required

        Test Type:
            Authorization / Security Test
        """
        # Act
        response = http_client.get(ENDPOINTS["me"])

        # Assert
        assert response.status_code == 401

    def test_get_user_info_with_invalid_token(self, http_client: httpx.Client):
        """
        Test: Retrieve User Info with Invalid Token

        Scenario:
            User provides malformed JWT token

        Expected Behavior:
            - API returns 401 Unauthorized
        """
        # Arrange
        invalid_token = "not.a.valid.jwt.token.xyz"

        # Act
        response = http_client.get(
            ENDPOINTS["me"], headers={"Authorization": f"Bearer {invalid_token}"}
        )

        # Assert
        assert response.status_code == 401

    def test_get_user_info_with_malformed_header(self, http_client: httpx.Client):
        """
        Test: Request with Malformed Authorization Header

        Scenario:
            Authorization header doesn't follow "Bearer <token>" format

        Expected Behavior:
            - API returns 401 Unauthorized

        Common Mistakes:
            - Missing "Bearer " prefix
            - Extra spaces
            - Wrong case (e.g., "bearer" instead of "Bearer")
        """
        # Arrange
        malformed_headers = ["Authorization: invalidtoken"]

        # Act
        response = http_client.get(
            ENDPOINTS["me"], headers={"Authorization": "invalidtoken"}
        )

        # Assert
        assert response.status_code == 401


# ============================================================================
# TEST SUITE: END-TO-END AUTHENTICATION FLOW
# ============================================================================


class TestEndToEndAuthFlow:
    """
    Test Suite: Complete Authentication Journey

    Purpose:
        Tests the complete user flow: Register → Login → Access Protected Resources

    Why End-to-End Tests Matter:
        - Unit tests verify individual functions
        - Integration tests verify components work together
        - E2E tests verify complete user workflows
        - Catches issues that don't show up in isolation
    """

    def test_complete_auth_flow_register_login_access(
        self, http_client: httpx.Client, unique_user_data: Dict[str, str]
    ):
        """
        Test: Complete Authentication Workflow

        Scenario:
            New user registers, logs in, and accesses their profile

        Test Flow:
            1. User registers with new credentials
            2. User logs in with same credentials
            3. User uses access token to retrieve their profile
            4. User refreshes token
            5. User uses new token to confirm still authenticated

        Expected Behavior:
            - All 5 steps succeed
            - All API responses match expectations

        Test Technique:
            Stateful Test - each step depends on previous
            Shows complete user journey through system
        """
        # Step 1: Register
        register_response = http_client.post(
            ENDPOINTS["register"],
            json={
                "username": unique_user_data["username"],
                "email": unique_user_data["email"],
                "password": unique_user_data["password"],
            },
        )
        assert register_response.status_code == 201

        # Step 2: Login
        login_response = http_client.post(
            ENDPOINTS["login"],
            json={
                "username": unique_user_data["username"],
                "password": unique_user_data["password"],
            },
        )
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access"]
        refresh_token = tokens["refresh"]

        # Step 3: Access protected resource
        me_response = http_client.get(
            ENDPOINTS["me"], headers={"Authorization": f"Bearer {access_token}"}
        )
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == unique_user_data["email"]

        # Step 4: Refresh token
        refresh_response = http_client.post(
            ENDPOINTS["refresh"], json={"refresh": refresh_token}
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        new_access_token = new_tokens["access"]

        # Step 5: Verify new token works
        me_response_2 = http_client.get(
            ENDPOINTS["me"], headers={"Authorization": f"Bearer {new_access_token}"}
        )
        assert me_response_2.status_code == 200


# ============================================================================
# PYTEST CONFIGURATION & HOOKS
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Fixture: Event Loop for Async Tests

    Purpose:
        Provides event loop for pytest-asyncio
        Allows running async/await test functions

    Usage:
        Not needed for current tests (all synchronous)
        But useful if you add async Playwright tests later
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# USAGE & RUNNING TESTS
# ============================================================================

"""
Running the Tests
=================

Prerequisites:
    1. Install dependencies:
       pip install pytest pytest-asyncio httpx playwright
       
    2. Start Django server:
       python manage.py runserver
       
Commands:
    Run all tests:
        pytest earfull_engine/tests/e2e/test_auth_flow.py -v
        
    Run specific test class:
        pytest earfull_engine/tests/e2e/test_auth_flow.py::TestUserRegistration -v
        
    Run specific test:
        pytest earfull_engine/tests/e2e/test_auth_flow.py::TestUserRegistration::test_successful_registration -v
        
    Run with detailed output:
        pytest earfull_engine/tests/e2e/test_auth_flow.py -vv
        
    Run with print statements:
        pytest earfull_engine/tests/e2e/test_auth_flow.py -s
        
    Run with coverage report:
        pytest earfull_engine/tests/e2e/test_auth_flow.py --cov=earfull_engine.accounts --cov-report=html

Test Results Output:
    - Each test shows as PASSED or FAILED
    - Failed tests show assertion error details
    - Coverage report shows what code paths are tested
"""
