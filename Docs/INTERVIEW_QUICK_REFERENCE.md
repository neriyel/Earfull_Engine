# QA Interview Quick Reference Card
*Keep this handy during your interview tomorrow*

---

## 🎯 The Elevator Pitch (30 seconds)

"I created comprehensive authentication tests for a Django JWT API using pytest and 
Playwright. The test suite includes 25+ tests covering registration, login, token 
management, and protected resource access. I tested both happy paths and error 
scenarios, with special focus on security - ensuring passwords aren't exposed and 
tokens are properly validated. Each test is well-documented to explain not just 
what is tested, but why it matters."

---

## 🔑 Key Terminology to Use

- **AAA Pattern:** Arrange (setup) → Act (execute) → Assert (verify)
- **Fixtures:** Reusable test setup/teardown code
- **Assertions:** Verifications that check expected behavior
- **Test Isolation:** Each test is independent, no dependencies
- **Negative Testing:** Testing error paths and invalid inputs
- **API Testing:** Testing endpoints directly (no UI)
- **Mock/Stub:** Fake object replacing real dependency (not used here - using real DB)
- **JWT Token:** JSON Web Token with header.payload.signature structure
- **Authentication:** Verifying who user is (username/password)
- **Authorization:** Verifying what user can do (access control)

---

## 🧪 My 5 Test Suites at a Glance

| Test Class | File | Tests | Purpose |
|-----------|------|-------|---------|
| TestUserRegistration | test_auth_flow.py | 5 | New user signup, validation |
| TestUserLogin | test_auth_flow.py | 5 | Login, token generation |
| TestTokenRefresh | test_auth_flow.py | 3 | Refresh token workflow |
| TestAuthenticatedRequests | test_auth_flow.py | 4 | Protected endpoint access |
| TestEndToEndAuthFlow | test_auth_flow.py | 1 | Complete user journey |

**Async/Advanced Suite:** test_auth_flow_playwright.py (6+ tests)
- Concurrent user testing
- Command parametrized scenarios
- Token security validation

---

## 🔒 Security Tests I Included

**Password Security:**
✓ Passwords hashed, not plaintext  
✓ Passwords never in API responses  
✓ Validate password strength

**Token Security:**
✓ Tokens validated before use  
✓ Invalid tokens rejected (401)  
✓ Token claims verified

**Authorization:**
✓ Users can't access other users' data  
✓ Unauthenticated requests rejected  
✓ Tokens can't be guessed/tampered

---

## 💻 Code Example to Discuss

```python
def test_successful_login(http_client, registered_user):
    """
    Test: Successful Login
    Scenario: Registered user provides correct credentials
    Expected: API returns 200 OK with access & refresh tokens
    """
    # ARRANGE - setup
    credentials = {
        "username": registered_user["username"],
        "password": registered_user["password"]
    }
    
    # ACT - execute
    response = http_client.post("/login/", json=credentials)
    
    # ASSERT - verify
    assert response.status_code == 200
    tokens = response.json()
    assert "access" in tokens
    assert "refresh" in tokens
```

**Can explain:**
- Why this test matters (core auth flow)
- AAA pattern structure
- What's being asserted and why
- How fixtures provide test data

---

## 📊 Response Codes to Know

| Code | Meaning | Example |
|------|---------|---------|
| 200 | OK | Login successful, token returned |
| 201 | Created | New user registered |
| 400 | Bad Request | Missing required fields |
| 401 | Unauthorized | Invalid token or wrong password |
| 403 | Forbidden | Valid token but no permission |
| 500 | Server Error | Database error, etc. |

---

## 🤔 Common Questions & Quick Answers

**Q: What tests did you write?**  
A: 25+ authentication tests covering registration, login, token refresh, and protected 
access. Half test success paths, half test error scenarios and edge cases.

**Q: Why fixtures?**  
A: Reduce code duplication and make tests independent. Each test gets fresh data, 
preventing interference between tests.

**Q: How many tests should we write?**  
A: Depends on risk. Authentication is high-risk, so comprehensive testing (25+) 
is justified. Less critical features might have fewer tests.

**Q: Why test error paths?**  
A: To ensure the system fails safely. If someone enters a wrong password, they 
should get a clear error - not a cryptic 500 error.

**Q: What makes a test good?**  
A: FIRST: Fast, Independent, Repeatable, Self-checking, Timely. Plus clear naming 
and documentation so anyone can understand it.

**Q: How do you prevent test data conflicts?**  
A: Use unique data (UUID + timestamp) for each test. Each test is independent.

**Q: Should tests be updated when requirements change?**  
A: Yes. Tests are documentation. Keep them in sync with requirements.

**Q: What's flaky test?**  
A: A test that sometimes passes, sometimes fails randomly. Usually caused by timing 
issues or test dependencies. Should be fixed or removed.

---

## 🎤 Confidence Boosters

**If you don't know something:**
- "I'm not familiar with that, but I'd like to learn. Is it similar to [related concept]?"
- "I haven't worked with that yet, but here's how I approach similar problems..."
- "That's a great question. Let me think about that..."

**If a test fails during interview:**
- "The test is checking [behavior]. The failure suggests [reason]. 
   We could investigate by [approach]."
- "This is actually a good example of why we test - to catch issues early."

**If asked to write a test live:**
1. Ask clarifying questions ("What endpoint? What should we test?")
2. Explain your approach before coding
3. Follow AAA pattern visibly
4. Talk through your assertions
5. Discuss edge cases

---

## 📖 Key Files

| File | Purpose | When to Reference |
|------|---------|------------------|
| AUTHENTICATION_TEST_INTERVIEW_GUIDE.md | Complete interview prep | Before interview |
| test_auth_flow.py | Main test file | Show examples |
| TESTING_README.md | How to run tests | If asked about setup |
| PROJECT_SUMMARY.md | Overview of all work | For context |

---

## ✅ Before Walking into Interview

- [ ] Review this card one more time
- [ ] Know your elevator pitch
- [ ] Understand AAA pattern
- [ ] Know what your 5 test classes test
- [ ] Be ready to explain 1-2 tests in detail
- [ ] Know JWT token basics
- [ ] Remember: it's about your THINKING process, not just the code

---

## 🚀 Parting Thoughts

You've done solid work here. You've demonstrated:
1. Understanding of authentication concepts
2. Knowledge of testing best practices
3. Ability to think about security
4. Strong documentation skills
5. Initiative and thorough thinking

Go in with confidence. Be ready to discuss your thinking process.
Show genuine interest in QA.
Ask thoughtful questions about their testing approach.

**You've got this! 💪**

---

Generated: March 2, 2026  
Use this card as reference during your interview tomorrow
