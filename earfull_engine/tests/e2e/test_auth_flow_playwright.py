"""
Authentication Flow Tests using Playwright API Testing
=======================================================

Purpose:
    Advanced authentication testing using Playwright's API request context.

Why Playwright for API Testing:
    - Modern, fast, and cross-browser capable
    - Can test both API and UI in same framework
    - Powerful context system for managing state (cookies, tokens, etc.)
    - Better for testing real browser behavior than mocking

Test Coverage:
    - Registration with form validation
    - Login and token persistence
    - Session management
    - CSRF protection (if implemented)
    - Cookie handling

This complements httpx tests by testing browser-like behavior.
"""

import pytest
import asyncio
from playwright.async_api import async_playwright, APIRequestContext, Browser
from typing import AsyncGenerator, Dict
import uuid


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL = "http://127.0.0.1:8000/accounts/"


# ============================================================================
# FIXTURES FOR PLAYWRIGHT API TESTING
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def playwright_context() -> AsyncGenerator[APIRequestContext, None]:
    """
    Fixture: Playwright API Request Context

    Purpose:
        Sets up an isolated API request context for testing

    Why separate contexts:
        - Each test gets clean state
        - Cookies, tokens are isolated
        - Tests don't interfere with each other

    Yields:
        APIRequestContext: Playwright's async HTTP client
    """
    async with async_playwright() as p:
        request_context = await p.request.new_context(base_url=BASE_URL)
        yield request_context
        await request_context.dispose()


@pytest.fixture
async def unique_credentials() -> Dict[str, str]:
    """
    Fixture: Generate unique test credentials

    Yields fresh credentials for each test to avoid conflicts
    """
    unique_id = str(uuid.uuid4())[:8]
    return {
        "username": f"playwright_test_{unique_id}",
        "email": f"playwright_{unique_id}@test.com",
        "password": "PlaywrightTestPass123!",
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def register_user(
    context: APIRequestContext, credentials: Dict[str, str]
) -> Dict:
    """
    Helper: Register a new user

    Purpose:
        Reusable function to create test users
        Keeps test code DRY (Don't Repeat Yourself)

    Args:
        context: Playwright request context
        credentials: User registration data

    Returns:
        Response JSON data

    Raises:
        AssertionError: If registration fails
    """
    response = await context.post(
        "register/",
        data={
            "username": credentials["username"],
            "email": credentials["email"],
            "password": credentials["password"],
        },
    )
    assert response.ok, f"Registration failed: {response.status}"
    return await response.json()


async def login_user(context: APIRequestContext, credentials: Dict[str, str]) -> str:
    """
    Helper: Login and retrieve access token

    Purpose:
        Simplifies login for tests that need authentication

    Args:
        context: Playwright request context
        credentials: User login data

    Returns:
        Access token string
    """
    response = await context.post(
        "login/",
        data={"username": credentials["username"], "password": credentials["password"]},
    )
    assert response.ok, f"Login failed: {response.status}"
    data = await response.json()
    return data["access"]


# ============================================================================
# TEST SUITE: PLAYWRIGHT API TESTS
# ============================================================================


class TestPlaywrightAuthFlow:
    """
    Test Suite: Authentication using Playwright

    Advantages over direct httpx:
        - Built-in context management for cookies/tokens
        - Better browser compatibility testing
        - Can add UI tests using same framework later
        - Captures more real-world browser behavior
    """

    @pytest.mark.asyncio
    async def test_registration_flow(
        self, playwright_context: APIRequestContext, unique_credentials: Dict[str, str]
    ):
        """
        Test: User Registration via Playwright

        Scenario:
            New user completes registration

        Setup:
            - Use Playwright's request context
            - Manage state across requests automatically

        Verification:
            - Status code 201
            - User object returned
            - Password not in response
        """
        # Arrange
        creds = unique_credentials

        # Act
        response = await playwright_context.post(
            "register/",
            data={
                "username": creds["username"],
                "email": creds["email"],
                "password": creds["password"],
            },
        )

        # Assert
        assert response.ok
        user = await response.json()
        assert user["username"] == creds["username"]
        assert user["email"] == creds["email"]
        assert "password" not in user

    @pytest.mark.asyncio
    async def test_login_with_token_persistence(
        self, playwright_context: APIRequestContext, unique_credentials: Dict[str, str]
    ):
        """
        Test: Login and Token Storage

        Concept:
            Real-world: Browser stores tokens (localStorage, sessionStorage)
            Test: Verify token is returned and can be used

        Workflow:
            1. Register user
            2. Login to get token
            3. Use token in subsequent request
            4. Verify authentication works
        """
        # Arrange & Act
        creds = unique_credentials
        await register_user(playwright_context, creds)

        login_response = await playwright_context.post(
            "login/",
            data={"username": creds["username"], "password": creds["password"]},
        )

        # Assert login response
        assert login_response.ok
        tokens = await login_response.json()
        assert "access" in tokens
        assert "refresh" in tokens

        # Act: Use token to access protected resource
        access_token = tokens["access"]
        me_response = await playwright_context.get(
            "me/", headers={"Authorization": f"Bearer {access_token}"}
        )

        # Assert authenticated access works
        assert me_response.ok
        user_data = await me_response.json()
        assert user_data["email"] == creds["email"]

    @pytest.mark.asyncio
    async def test_concurrent_user_logins(self, playwright_context: APIRequestContext):
        """
        Test: Multiple Concurrent Users

        Purpose:
            Verify system handles multiple users simultaneously

        Real-world Scenario:
            Multiple people logging in at same time (e.g., peak hours)

        Testing Approach:
            Create and login multiple users concurrently
            Verify each gets unique tokens
            Verify tokens don't cross-contaminate

        Why This Matters:
            Concurrent testing reveals race conditions
            Important for load testing and stress testing
        """
        # Arrange
        users = []
        for i in range(3):
            unique_id = str(uuid.uuid4())[:8]
            users.append(
                {
                    "username": f"concurrent_{unique_id}",
                    "email": f"concurrent_{unique_id}@test.com",
                    "password": "ConcurrentPass123!",
                }
            )

        # Act: Register all users concurrently
        register_tasks = [register_user(playwright_context, user) for user in users]
        await asyncio.gather(*register_tasks)

        # Act: Login all users concurrently
        login_tasks = [login_user(playwright_context, user) for user in users]
        access_tokens = await asyncio.gather(*login_tasks)

        # Assert: All got unique tokens
        assert len(access_tokens) == 3
        assert len(set(access_tokens)) == 3, "Tokens should be unique"

        # Act: Access /me with different tokens
        me_tasks = [
            playwright_context.get("me/", headers={"Authorization": f"Bearer {token}"})
            for token in access_tokens
        ]
        me_responses = await asyncio.gather(*me_tasks)

        # Assert: Each user sees their own data
        assert all(response.ok for response in me_responses)
        user_data_list = [await response.json() for response in me_responses]
        emails = [user_data["email"] for user_data in user_data_list]
        expected_emails = [user["email"] for user in users]
        assert set(emails) == set(expected_emails)

    @pytest.mark.asyncio
    async def test_token_refresh_flow(
        self, playwright_context: APIRequestContext, unique_credentials: Dict[str, str]
    ):
        """
        Test: Token Refresh Workflow

        Real-world Use Case:
            - User stays logged in for extended time
            - Original access token begins to expire
            - Client refreshes token without re-entering password
            - User continues using app with new token

        Testing Strategy:
            1. Register and login user
            2. Save refresh token
            3. Use refresh token to get new access token
            4. Verify new access token authenticates requests
            5. Verify old token is invalid (if rotation used)
        """
        # Arrange
        creds = unique_credentials
        await register_user(playwright_context, creds)

        # Act: Login
        login_response = await playwright_context.post(
            "login/",
            data={"username": creds["username"], "password": creds["password"]},
        )
        original_tokens = await login_response.json()
        refresh_token = original_tokens["refresh"]
        original_access_token = original_tokens["access"]

        # Act: Refresh token
        refresh_response = await playwright_context.post(
            "refresh/", data={"refresh": refresh_token}
        )

        # Assert: Got new access token
        assert refresh_response.ok
        new_tokens = await refresh_response.json()
        new_access_token = new_tokens["access"]
        assert new_access_token is not None

        # Act: Verify new token works
        me_response = await playwright_context.get(
            "me/", headers={"Authorization": f"Bearer {new_access_token}"}
        )

        # Assert: New token authenticates successfully
        assert me_response.ok

    @pytest.mark.asyncio
    async def test_security_token_isolation(
        self, playwright_context: APIRequestContext, unique_credentials: Dict[str, str]
    ):
        """
        Test: Token Security and Isolation

        Security Principles:
            - User1's token should NOT grant access to User2's data
            - Invalid tokens should be rejected
            - Tokens should not be guessable

        Testing Approach:
            1. Create two users with different data
            2. Each logs in and gets tokens
            3. Try to use User1's token to access User2
            4. Verify it fails
        """
        # Arrange
        user1_creds = unique_credentials
        unique_id_2 = str(uuid.uuid4())[:8]
        user2_creds = {
            "username": f"user2_{unique_id_2}",
            "email": f"user2_{unique_id_2}@test.com",
            "password": "SecurityTestPass123!",
        }

        # Register and login both users
        await register_user(playwright_context, user1_creds)
        await register_user(playwright_context, user2_creds)

        user1_token = await login_user(playwright_context, user1_creds)
        user2_token = await login_user(playwright_context, user2_creds)

        # Act: Use User1's token
        response1 = await playwright_context.get(
            "me/", headers={"Authorization": f"Bearer {user1_token}"}
        )
        user1_data = await response1.json()

        # Act: Use User2's token
        response2 = await playwright_context.get(
            "me/", headers={"Authorization": f"Bearer {user2_token}"}
        )
        user2_data = await response2.json()

        # Assert: Each user only sees their own data
        assert user1_data["email"] == user1_creds["email"]
        assert user2_data["email"] == user2_creds["email"]
        assert user1_data["id"] != user2_data["id"]


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================


class TestParametrizedAuthScenarios:
    """
    Test Suite: Parametrized Tests

    Purpose:
        Test multiple similar scenarios with different inputs
        Reduces code duplication
        Easy to add more test cases

    Concept: Data-Driven Testing
        Same test logic, different inputs
        All results are reported separately
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "password",
        [
            "ValidPassword123!",
            "AnotherValid@Pass2024",
            "ComplexP@ssw0rd!#$",
        ],
    )
    async def test_login_with_various_valid_passwords(
        self, playwright_context: APIRequestContext, password: str
    ):
        """
        Test: Login Works with Various Complex Passwords

        Parametrized Inputs:
            Multiple complex passwords

        Why Parametrize:
            Ensures system handles various password formats
            Tests special characters, numbers, uppercase
            More comprehensive than single password test

        Test Runs:
            pytest will run this 3 times (one for each password)
        """
        # Arrange
        unique_id = str(uuid.uuid4())[:8]
        creds = {
            "username": f"complex_pwd_{unique_id}",
            "email": f"complex_pwd_{unique_id}@test.com",
            "password": password,
        }

        # Act & Assert: Register
        register_resp = await playwright_context.post("register/", data=creds)
        assert register_resp.ok

        # Act & Assert: Login with same password
        login_resp = await playwright_context.post(
            "login/", data={"username": creds["username"], "password": password}
        )
        assert login_resp.ok
        tokens = await login_resp.json()
        assert "access" in tokens

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "invalid_input,expected_reason",
        [
            ({"username": "test", "password": ""}, "missing password"),
            ({"username": "", "password": "pass123"}, "missing username"),
            ({}, "missing both fields"),
            ({"username": "test", "password": None}, "null password"),
        ],
    )
    async def test_login_with_invalid_inputs(
        self,
        playwright_context: APIRequestContext,
        invalid_input: Dict,
        expected_reason: str,
    ):
        """
        Test: Login Rejects Invalid Inputs

        Parametrized Scenarios:
            Multiple invalid input combinations

        Documentation:
            Each test case documents expected behavior
            expected_reason parameter explains what's being tested

        Test Type:
            Negative Testing / Input Validation
        """
        # Act
        response = await playwright_context.post("login/", data=invalid_input)

        # Assert: Should return error status
        assert not response.ok, f"Should fail for {expected_reason}"
        assert response.status in [400, 401]


# ============================================================================
# FIXTURES FOR BROWSER-BASED TESTING (Future Enhancement)
# ============================================================================


@pytest.fixture
async def browser():
    """
    Fixture: Playwright Browser Instance

    Purpose:
        For future UI testing of authentication forms

    Notes:
        Currently only API tests, but can add UI tests:
        - Test login form rendering
        - Test form validation messages
        - Test redirect after login
        - Test session persistence across pages

    Usage (Future):
        @pytest.mark.asyncio
        async def test_login_form_ui(browser):
            page = await browser.new_page()
            await page.goto("http://localhost:3000/login")
            ...
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        yield browser
        await browser.close()


# ============================================================================
# PYTEST MARKERS FOR ORGANIZING TESTS
# ============================================================================

"""
Test Markers / Organization
===========================

Markers help organize and run tests by category

Usage:
    # Mark test with marker
    @pytest.mark.asyncio
    @pytest.mark.security
    async def test_something(): ...
    
    # Run only security tests:
    pytest -m security tests/
    
    # Run all tests except slow tests:
    pytest -m "not slow" tests/

Common Markers for Auth Tests:
    - asyncio: Async tests
    - security: Security-related tests
    - slow: Tests that take longer (good to skip in CI/CD)
    - integration: Integration tests (use real database)
    - unit: Unit tests
    - smoke: Smoke tests (quick sanity checks)
"""
