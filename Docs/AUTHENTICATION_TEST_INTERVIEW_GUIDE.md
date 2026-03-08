"""
=============================================================================
AUTHENTICATION TESTING - INTERVIEW PREPARATION GUIDE
=============================================================================

Date: March 2, 2026
Purpose: Help prepare for QA Manager & QA Senior Lead interview
Context: Testing JWT-based authentication flows

This document covers:
1. Testing Fundamentals
2. Authentication Testing Strategy
3. Test Design & Documentation
4. Interview Talking Points
5. Common QA Questions & Answers
6. Best Practices & Quality Metrics

=============================================================================
PART 1: TESTING FUNDAMENTALS
=============================================================================

1.1 TYPES OF TESTING
-------------------

Manual Testing:
    Definition: Human tester manually executing test cases
    When to use: UI exploration, accessibility, user experience validation
    Pros: Flexible, catches unexpected issues, good for edge cases
    Cons: Time-consuming, not repeatable, hard to scale
    
Automated Testing:
    Definition: Running pre-written test scripts automatically
    When to use: Regression testing, repeated scenarios, CI/CD pipeline
    Pros: Fast, repeatable, catches regressions, scalable
    Cons: Expensive to set up, limited edge case coverage, needs maintenance
    
Our Strategy: Hybrid
    - Automated for core workflows (register → login → access)
    - Manual for UX/UI edge cases
    - Automated for security scenarios


1.2 TEST PYRAMID
----------------

    /\\          End-to-End Tests (5%)
   /  \\         - Complete user journeys
   /----\\       - Slow, costly, cover most features
  /      \\
 / _______ \\    Integration Tests (15%)
 /         \\    - Multiple components working together
 /__________\\   - Database, external services
 
/____________\\  Unit Tests (80%)
               - Single functions/methods
               - Fast, cheap, good coverage


Our Testing Plan Follows This:
- Unit Tests: Individual auth methods (password hashing, token validation)
- Integration Tests: /register + /login flow together
- E2E Tests: full auth journey (register → login → /me → refresh → /me)


1.3 TESTING STYLES / METHODOLOGIES
----------------------------------

AAA Pattern (Arrange-Act-Assert):
    Arrange: Set up test data and preconditions
    Act: Execute the code being tested
    Assert: Verify results match expectations
    
    Benefits:
    - Clear structure
    - Easy to read and understand
    - Easy to debug when tests fail

TDD (Test-Driven Development):
    1. Write test that fails (Red)
    2. Write code to make test pass (Green)
    3. Refactor code (Refactor)
    
    Benefits:
    - Tests define requirements upfront
    - Better code design
    - High test coverage guaranteed

BDD (Behavior-Driven Development):
    Write tests in business language:
    "Given a new user
     When they register with valid credentials
     Then they receive a confirmation email"
    
    Benefits:
    - Non-technical people can read tests
    - Business requirements are documentation
    - Tests and requirements stay in sync

We're Using: AAA + some BDD concepts (descriptive test names)


1.4 WHAT TO TEST vs NOT TO TEST
-------------------------------

Should Test:
    ✓ Core business logic (auth flows)
    ✓ Security boundaries (auth checks)
    ✓ Error handling (invalid passwords)
    ✓ Data validation (username uniqueness)
    ✓ Integration points (database)

Should NOT Test:
    ✗ Third-party library behavior (JWT library)
    ✗ Infrastructure (Django itself)
    ✗ Browser rendering (unless UI testing)
    ✗ Network latency (simulate stable connection)

Why Skip These:
    - Already tested by library authors
    - Slow and flaky
    - Not your responsibility
    - Outside application boundary


=============================================================================
PART 2: AUTHENTICATION TESTING STRATEGY
=============================================================================

2.1 AUTHENTICATION FLOWS TO TEST
-------------------------------

Basic Registration Flow:
    User Input → Username Validation → Email Validation → Password Hashing
    → Database Insert → Return User Object
    
    Test Cases:
    ✓ Successful registration
    ✗ Duplicate username
    ✗ Duplicate email
    ✗ Missing required fields
    ✗ Invalid email format

Login / Token Generation Flow:
    User Input → Hash Password → Compare with DB → Generate JWT Tokens
    → Return Access & Refresh Tokens
    
    Test Cases:
    ✓ Successful login
    ✗ User not found
    ✗ Wrong password
    ✗ Locked account (if implemented)
    ✗ Expired credentials

Protected Resource Access:
    Authorization Header → Token Validation → Claims Check → Return Data
    
    Test Cases:
    ✓ Valid token
    ✗ Missing token
    ✗ Invalid token
    ✗ Expired token
    ✗ Malformed header

Token Refresh:
    Refresh Token → Validate → Generate New Access Token
    
    Test Cases:
    ✓ Valid refresh token
    ✗ Invalid token
    ✗ Expired token
    ✗ Token rotation (advanced)


2.2 JWT AUTHENTICATION CONCEPTS TO DISCUSS
------------------------------------------

JWT Structure:
    header.payload.signature
    
    Header: Algorithm info (HS256, RS256, etc.)
    Payload: Claims (user ID, permissions, issued time)
    Signature: Cryptographic proof of authenticity
    
    Example:
    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
    eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.
    SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
    
    Benefits:
    - Stateless (no server-side session storage)
    - Can be used across multiple services
    - Self-contained (token includes user info)

Token Lifespan:
    Access Token: Short-lived (15 min - 1 hour)
    - Use for API requests
    - Frequent rotation reduces risk if stolen
    
    Refresh Token: Long-lived (days/weeks)
    - Use to get new access tokens
    - Stored securely on client
    - Rarely sent to server

Why Two Tokens:
    Security: If access token exposed, damage is limited
    Performance: Don't need to re-authenticate frequently
    UX: Users stay logged in without re-entering password


2.3 TESTING SECURITY ASPECTS
---------------------------

Password Security:
    Test that:
    ✓ Passwords not stored in plaintext (use hashing with salt)
    ✓ Passwords not in API responses
    ✓ Passwords not in logs
    ✓ Minimum password strength (length, complexity)
    ✓ Password reset tokens are short-lived
    
    How to Test:
    - Verify hash algorithm used (bcrypt, Argon2, etc.)
    - Check database for plaintext passwords (should fail)
    - Inspect API responses for any password fields
    - Review logs for sensitive data

Token Security:
    Test that:
    ✓ Tokens not in URL (query params)
    ✓ Tokens sent via Authorization header only
    ✓ Tokens validated server-side before trusting
    ✓ Token signature verified
    ✓ Token expiration enforced
    
    How to Test:
    - Attempt invalid URL: /api/me?token=xxx (should fail)
    - Attempt tampered token (modify signature)
    - Attempt expired token
    - Verify 401 response for invalid tokens

Authorization:
    Test that:
    ✓ User can only access their own data
    ✓ User2's token can't access User1's resources
    ✓ Admin/user role separation (if implemented)
    ✓ Rate limiting (prevent brute force)
    
    How to Test:
    - Create two users, get both tokens
    - Try to fetch data with wrong user's token
    - Should get 403 Forbidden or 401 Unauthorized


=============================================================================
PART 3: TEST DESIGN & DOCUMENTATION
=============================================================================

3.1 TEST DATA MANAGEMENT
-----------------------

Test Data Strategy:
    Unique per Test:
    - Prevents test interference
    - Each test independent
    - Can run in any order
    - Parallelizable
    
    Implementation:
    - Use fixtures to generate unique data
    - UUID for uniqueness
    - Clean up after test (delete test user from DB)

Example:
    @pytest.fixture
    def unique_user_data():
        unique_id = str(uuid.uuid4())[:8]
        return {
            "username": f"testuser_{unique_id}",
            "email": f"test_{unique_id}@test.com",
            "password": "TestPass123!"
        }


3.2 TEST FIXTURES
-----------------

What are Fixtures:
    Reusable setup/teardown code for tests
    Reduces duplication
    Improves readability
    Handles cleanup automatically

Fixture Scopes:
    function (default): Fresh for each test
    class: Shared within test class
    module: Shared across test file
    session: Shared across all tests in run
    
    Choose based on needs:
    - Use 'function' for isolated tests
    - Use 'session' for expensive setup (DB connection)

Our Fixtures:
    http_client: Fresh HTTP client each test
    unique_user_data: Unique credentials each test
    registered_user: Pre-created user for login tests


3.3 TEST NAMING CONVENTIONS
--------------------------

Good Test Name Format:
    test_<method>_<scenario>_<expected_result>
    
Examples:
    test_register_with_valid_credentials_returns_201
    test_login_with_wrong_password_returns_401
    test_protected_endpoint_without_token_returns_401
    
Benefits:
    - Self-documenting
    - Clear what's being tested
    - Clear what should happen
    - Issues are easy to find

File Organization:
    tests/
    ├── unit/           # Individual methods
    ├── integration/    # Components together
    ├── e2e/           # Full user journeys
    └── fixtures/      # Shared test data
    
Test Class Organization:
    Organize by feature:
    class TestUserRegistration:
    class TestUserLogin:
    class TestTokenRefresh:
    
    Tests grouped logically
    Easy to focus on specific feature


3.4 DOCUMENTATION IN TESTS
--------------------------

Documentation Levels:

Module Level:
"""Module Purpose, Scope, Dependencies"""

Class Level:
"""Feature being tested, User stories, Test strategy"""

Method Level:
"""Scenario, Expected behavior, Test technique"""

Inline Comments:
# Explain WHY, not WHAT (code shows the what)


Example:
class TestUserLogin:
    '''
    Test Suite: User Login
    
    Scope: POST /login/ endpoint
    
    User Story: As a registered user, I want to login
    and receive JWT tokens for API access
    
    Test Strategy: Test happy path and error scenarios
    '''
    
    def test_successful_login(...):
        '''
        Test: Successful Login
        
        Scenario: User provides correct credentials
        Expected: Returns 200 OK with access & refresh tokens
        Technique: AAA Pattern
        '''
        # Arrange: Prepare test data
        # Act: Execute login
        # Assert: Verify response


=============================================================================
PART 4: INTERVIEW TALKING POINTS
=============================================================================

4.1 HOW TO DISCUSS THESE TESTS
------------------------------

What they are:
    "I've created comprehensive authentication tests using pytest and Playwright.
     The tests cover registration, login, token refresh, and protected API access.
     I'm using both synchronous (httpx) and asynchronous (Playwright) API clients
     to test different scenarios."

Test Coverage:
    "The test suite includes:
     - Happy paths (successful auth flows)
     - Negative tests (error scenarios)
     - Security tests (token validation, access control)
     - Edge cases (duplicate users, invalid inputs)
     - End-to-end flows (complete user journey)"

Test Framework Choices:
    "I chose pytest for its powerful fixture system and clear syntax.
     Fixtures eliminate code duplication and make tests more maintainable.
     I used httpx for synchronous API testing and Playwright's async API client
     for more advanced scenarios."

Documentation Approach:
    "Each test is heavily documented with:
     - Docstrings explaining scenario and expected behavior
     - Inline comments explaining testing concepts
     - AAA pattern making tests easy to understand
     - Test class organization by feature"


4.2 ANSWERING COMMON INTERVIEW QUESTIONS
----------------------------------------

Q: "How do you approach writing tests?"
A: "I follow the AAA pattern: Arrange (setup), Act (execute), Assert (verify).
   I start by understanding the requirements, then write tests for:
   1. Happy path (normal usage)
   2. Error scenarios (what can go wrong)
   3. Edge cases (boundary conditions)
   4. Security concerns (authorization, validation)
   
   I document each test with clear scenario, expected behavior, and reasoning."

Q: "What's the difference between unit and integration tests?"
A: "Unit tests test individual functions in isolation, mocking dependencies.
   Integration tests test multiple components working together using real dependencies.
   
   For auth:
   - Unit: Test password hashing function
   - Integration: Test registration saves to database
   - E2E: Test complete journey from register to login to protected resource"

Q: "How do you handle test data?"
A: "I use fixtures to generate unique test data for each test.
   This prevents tests from interfering with each other and allows parallel execution.
   Each test is independent and can run in any order.
   I use UUIDs to ensure uniqueness across multiple test runs."

Q: "What's the most important thing to test in authentication?"
A: "Security boundaries - making sure unauthorized users can't access protected resources.
   Specifically:
   1. Valid tokens grant access
   2. Invalid tokens are rejected
   3. Tampered tokens are rejected
   4. User can't access other user's data
   5. Passwords are never exposed in responses/logs
   
   These are critical for user security and data privacy."

Q: "How do you make tests maintainable?"
A: "Through good organization and documentation:
   1. Clear test names that describe what's being tested
   2. Fixtures for reusable setup code
   3. Helper functions for common operations
   4. Good documentation explaining WHY tests exist
   5. Avoiding magic values (use named constants)
   6. Keeping tests focused (one behavior per test)"

Q: "What would you do for testing at scale?"
A: "Several strategies:
   1. Organize by test type (unit/integration/e2e)
   2. Use test markers to categorize tests
   3. Run unit tests frequently (fast feedback)
   4. Run integration tests before deployment
   5. Run E2E tests in staging environment
   6. Use CI/CD pipeline for automated test execution
   7. Monitor test results and failure rates
   8. Maintain test health (remove flaky tests)"

Q: "How do you test security?"
A: "By thinking like an attacker:
   1. What if I use someone else's token?
   2. What if I modify the token?
   3. What if I don't send a token?
   4. What if I send an expired token?
   5. Can I guess a valid token?
   6. Can I brute force a password?
   7. Are passwords stored safely?
   8. Are tokens in logs?
   
   Then write tests that verify these attack vectors fail."


4.3 DEMONSTRATING TEST THINKING
-------------------------------

"Looking at the /login/ endpoint, I need to test:

- Happy Path: Valid credentials → 200 OK with tokens
- User doesn't exist: → 401 Unauthorized
- Wrong password: → 401 Unauthorized
- Missing username: → 400 Bad Request
- Missing password: → 400 Bad Request
- SQL injection attempt: → Rejected safely
- Rate limiting: → After N attempts, reject

For each scenario, I verify:
- Correct HTTP status code
- Response body structure
- No sensitive data in response

I also consider:
- What happens if database is slow?
- What if user is locked (brute force attempt)?
- What if email is unverified?
- What if password expired?"


=============================================================================
PART 5: COMMON QA QUESTIONS & ANSWERS
=============================================================================

Q: "What is a test case?"
A: "A test case is a set of conditions/inputs that tests specific functionality.
   Components:
   - Preconditions: What must be true before test
   - Test steps: What we do
   - Expected result: What should happen
   - Postconditions: Cleanup after test"

Q: "What's the difference between a bug and a defect?"
A: "Technically they're the same thing. Bug/defect = something not working as designed.
   As a tester, I report bugs by describing:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Screenshots/logs if applicable
   - Impact (critical, high, medium, low)"

Q: "What's a flaky test?"
A: "A test that sometimes passes and sometimes fails, unpredictably.
   Causes:
   - Race conditions
   - Timing issues
   - Test order dependency
   - External service availability
   - Insufficient test data cleanup
   
   Solutions:
   - Use unique test data per test
   - Add proper waits
   - Isolate tests (run in any order)
   - Mock external services
   - Clean up properly"

Q: "What makes a good test?"
A: "FIRST principle:
   - Fast: Should run quickly
   - Independent: Not dependent on other tests
   - Repeatable: Consistent results
   - Self-checking: Clear pass/fail
   - Timely: Written close to functionality
   
   Additionally:
   - Clear and readable
   - Tests one behavior
   - Has descriptive name
   - Well documented"

Q: "How do you prioritize what to test?"
A: "Risk-based testing:
   High Risk / High Impact → Test thoroughly
   - Authentication & authorization
   - Payment processing
   - Data deletion
   - Security
   
   Medium Risk → Standard testing
   - Normal workflows
   - Data modification
   - Error handling
   
   Low Risk → Minimal testing
   - UI styling
   - Localization
   - Non-critical features
   
   For auth specifically, everything is HIGH risk."

Q: "What's the difference between verification and validation?"
A: "Verification: Are we building the product right?
   - Does code match design specification?
   - Does API accept correct inputs?
   - Does output format match requirements?
   - Automated tests verify these
   
   Validation: Are we building the right product?
   - Does product meet user needs?
   - Is user experience good?
   - Does it solve the problem?
   - Manual tests + user feedback validate these"


=============================================================================
PART 6: BEST PRACTICES FOR QA TESTING
=============================================================================

6.1 TESTING BEST PRACTICES
--------------------------

1. Test Early and Often
   - Start testing as soon as code is written
   - Shift left (test requirements, not just code)
   - Continuous testing in CI/CD

2. Test Different Scenarios
   - Happy paths (normal usage)
   - Negative paths (error cases)
   - Edge cases (boundary conditions)
   - Alternative flows

3. Keep Tests Focused
   - One assertion per test (ideally)
   - Test one behavior
   - Easy to understand what failed

4. Use Descriptive Names
   - test_name should describe what's tested
   - Should read like documentation
   - No ambiguity

5. DRY Tests
   - Don't repeat code (use fixtures/helpers)
   - Common setup in setUp methods
   - Parametrize similar tests

6. Test Isolation
   - No test should depend on another
   - Fresh data per test
   - Run in any order
   - Run in parallel

7. Automate the Right Things
   - Core workflows (high impact)
   - Repeated scenarios (save time)
   - Regression prevention (catch regressions)
   - Don't automate UI pixel testing

8. Use Version Control
   - Tests in Git like code
   - Track test changes
   - Collaborate on tests

9. Document Tests
   - Explain WHY test exists
   - Link to requirements
   - Hard ot-read tests aren't maintained

10. Maintain Tests
    - Remove flaky tests
    - Update when requirements change
    - Regular refactoring
    - Reduce noise (ignore known issues)


6.2 TESTING ANTI-PATTERNS TO AVOID
---------------------------------

❌ Don't: Test implementation details
✓ Do: Test behavior

❌ Don't: Have many assertions per test
✓ Do: One behavior per test

❌ Don't: Use magic numbers
✓ Do: Use named constants

❌ Don't: Require tests to run in specific order
✓ Do: Make tests independent

❌ Don't: Leave test data in database
✓ Do: Clean up after each test

❌ Don't: Test third-party libraries
✓ Do: Test your code's integration with them

❌ Don't: Ignore flaky tests
✓ Do: Fix or remove them

❌ Don't: Write tests without understanding requirements
✓ Do: Read requirements first

❌ Don't: Copy-paste test code
✓ Do: Use fixtures and helpers


6.3 MEASURING TEST QUALITY
--------------------------

Code Coverage:
    - Percentage of code executed by tests
    - Higher ≠ Better (can test meaningless paths)
    - Aim for 80%+ on critical code
    - Authentication code should have 95%+

Test Execution Time:
    - Unit tests: < 1 second
    - Integration: < 10 seconds
    - E2E tests: < 1 minute (each)
    - Total suite: < 10 minutes

Pass Rate:
    - Should be high normally
    - Investigate all failures
    - Flaky tests are problems

Test/Code Ratio:
    - Critical code: 1:3+ test to code ratio
    - Normal code: 1:1 test to code ratio
    - Helper code: 1:0.5 or less

Defect Escape Rate:
    - How many bugs reach production?
    - Should be very low
    - Improve testing if too high


=============================================================================
PART 7: DEMONSTRATION POINTS
=============================================================================

Show and Discuss:

1. Test File Organization
   "Here are my different test files organized by type..."
   - test_auth_flow.py (synchronous)
   - test_auth_flow_playwright.py (asynchronous)
   "Clear structure makes tests easy to navigate"

2. Test Fixtures
   "I use fixtures to generate unique test data..."
   - Show @pytest.fixture decorators
   - Explain unique_user_data fixture
   "This ensures tests don't interfere with each other"

3. Test Documentation
   "Each test has multiple levels of documentation..."
   - Module docstrings
   - Class docstrings
   - Method docstrings
   - Inline comments
   "Documentation helps everyone understand the tests"

4. Test Scenarios
   "I test both success and failure paths..."
   - Show successful registration test
   - Show duplicate username test
   - Show missing password test
   "This prevents regressions and catches edge cases"

5. AAA Pattern
   "I follow Arrange-Act-Assert pattern..."
   - Arrange section (setup)
   - Act section (execute)
   - Assert section (verify)
   "Makes tests clear and organized"

6. Assertions
   "I verify multiple aspects of responses..."
   - Status code (200, 201, 400, 401)
   - Response body structure
   - Data correctness
   - Security checks (password not in response)
   "Different assertions ensure complete verification"


=============================================================================
PART 8: INTERVIEW DAY TIPS
=============================================================================

Before the Interview:
   □ Review authentication concepts (JWT, tokens, etc.)
   □ Understand the test code you wrote
   □ Be ready to explain each test
   □ Know the testing terminology
   □ Practice explaining complex tests simply
   □ Have examples ready

During the Interview:
   ✓ Speak clearly and confidently
   ✓ Take time to think before answering
   ✓ Give complete but concise answers
   ✓ Use examples from your code
   ✓ Admit if you don't know something
   ✓ Ask clarifying questions
   ✓ Show enthusiasm for testing
   ✓ Explain your thinking process

Red Flags to Avoid:
   ✗ "I don't know about that"
   ✗ Vague answers without examples
   ✗ Defensive responses to questions
   ✗ Refusing to discuss limitations
   ✗ "People usually just do X" instead of "I do X"

Good Responses to Common Situations:

If asked about your testing experience:
   "While I don't have formal QA experience yet, I've studied testing principles
   and put them into practice by designing a comprehensive test suite for our
   authentication system. I understand the importance of good testing and am
   eager to learn and apply professional testing standards."

If asked about a testing concept you don't know:
   "I'm not familiar with that specific approach, but I'd like to learn.
   It sounds like it's related to [related concept I do know].
   Could you explain how it works?"

If a test fails during interview:
   "Let's see what's happening. The test is checking [behavior].
   The failure suggests [likely cause]. We could investigate by [process].
   This is a good reminder of why we test - to catch issues early."


=============================================================================
QUICK REFERENCE CHECKLIST
=============================================================================

Before submitting your tests:
□ All tests have descriptive names
□ All test classes have docstrings explaining scope
□ All test methods have docstrings explaining scenario
□ Tests follow AAA pattern
□ No test data is hardcoded
□ Each test is independent
□ Tests can run in any order
□ No hardcoded timeouts/delays
□ Security scenarios are tested
□ Error paths are tested
□ Response codes are verified
□ Response body structure is verified
□ No sensitive data in responses

Interview day review:
□ Know what each test file tests
□ Know why each test exists
□ Be ready to explain any test
□ Know testing terminology
□ Understand JWT authentication
□ Know what to test in auth systems
□ Have examples ready
□ Be ready to discuss improvements
□ Be prepared to write a test live
□ Know your test framework (pytest)


=============================================================================
FINAL THOUGHTS
=============================================================================

These tests demonstrate:
1. Understanding of authentication flows
2. Knowledge of testing best practices
3. Attention to security (testing authorization)
4. Good code organization and documentation
5. Willingness to learn and improve

Go into the interview with confidence. You've done solid work here.
Focus on explaining your thinking, not just the code.
QA managers want to know HOW you think about testing, not just that you can write tests.

Good luck tomorrow! 🎯

=============================================================================
"""
