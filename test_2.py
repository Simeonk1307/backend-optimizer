#!/usr/bin/env python3
"""
Backend Obliterator - Advanced Test Suite
80+ tests designed to break systems and find edge cases
"""

import requests
import json
import time
import hashlib
import base64
import random
import string
import concurrent.futures
from typing import Dict, Optional, List
import sys
import threading

BASE_URL = "http://localhost:8080"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    END = '\033[0m'

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        self.lock = threading.Lock()
    
    def pass_test(self, name: str):
        with self.lock:
            self.passed += 1
            print(f"{Colors.GREEN}✓{Colors.END} {name}")
    
    def fail_test(self, name: str, reason: str):
        with self.lock:
            self.failed += 1
            self.errors.append(f"{name}: {reason}")
            print(f"{Colors.RED}✗{Colors.END} {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{Colors.BLUE}{'='*80}{Colors.END}")
        print(f"{Colors.CYAN}Backend Obliterator Results{Colors.END}")
        print(f"{Colors.BLUE}{'='*80}{Colors.END}")
        print(f"Total Tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.passed} ({100*self.passed//total if total > 0 else 0}%){Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed} ({100*self.failed//total if total > 0 else 0}%){Colors.END}")
        if self.errors:
            print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        print(f"{Colors.BLUE}{'='*80}{Colors.END}")
        return self.failed == 0

results = TestResults()

def rand_str(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

print(f"{Colors.MAGENTA}╔══════════════════════════════════════════════════════════════╗{Colors.END}")
print(f"{Colors.MAGENTA}║  BACKEND OBLITERATOR - EXTREME STRESS TEST SUITE            ║{Colors.END}")
print(f"{Colors.MAGENTA}║  Target: {BASE_URL:50s} ║{Colors.END}")
print(f"{Colors.MAGENTA}╚══════════════════════════════════════════════════════════════╝{Colors.END}\n")

# =============================================================================
# SECTION 1: AUTHENTICATION BREAKING TESTS (Tests 1-20)
# =============================================================================
print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
print(f"{Colors.YELLOW}SECTION 1: AUTHENTICATION BREAKING TESTS (20 tests){Colors.END}")
print(f"{Colors.YELLOW}{'='*80}{Colors.END}")

# Test 1: Register with minimum valid data
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "a",
        "password": "p",
        "display_name": "D"
    })
    if response.status_code == 201:
        results.pass_test("T001: Register with single char fields")
    else:
        results.fail_test("T001: Register with single char fields", f"Status {response.status_code}")
except Exception as e:
    results.fail_test("T001: Register with single char fields", str(e))

# Test 2: Register with empty strings (should fail)
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "",
        "password": "",
        "display_name": ""
    })
    if response.status_code == 400:
        results.pass_test("T002: Reject empty string fields")
    else:
        results.fail_test("T002: Reject empty string fields", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T002: Reject empty string fields", str(e))

# Test 3: Register with only whitespace (should fail)
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "   ",
        "password": "   ",
        "display_name": "   "
    })
    if response.status_code == 400:
        results.pass_test("T003: Reject whitespace-only fields")
    else:
        results.fail_test("T003: Reject whitespace-only fields", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T003: Reject whitespace-only fields", str(e))

# Test 4: Register with SQL injection attempt
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "admin' OR '1'='1",
        "password": "password",
        "display_name": "SQL Injection"
    })
    if response.status_code in [201, 400]:
        results.pass_test("T004: Handle SQL injection in username")
    else:
        results.fail_test("T004: Handle SQL injection in username", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T004: Handle SQL injection in username", str(e))

# Test 5: Register with XSS attempt
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "<script>alert('xss')</script>",
        "password": "password",
        "display_name": "<img src=x onerror=alert(1)>"
    })
    if response.status_code == 201:
        data = response.json()
        if "<script>" not in data.get("username", ""):
            results.pass_test("T005: Handle XSS in fields")
        else:
            results.fail_test("T005: Handle XSS in fields", "XSS not escaped")
    else:
        results.pass_test("T005: Handle XSS in fields (rejected)")
except Exception as e:
    results.fail_test("T005: Handle XSS in fields", str(e))

# Test 6: Register with very long username
try:
    long_username = "a" * 10000
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": long_username,
        "password": "password",
        "display_name": "Long"
    })
    if response.status_code in [201, 400]:
        results.pass_test("T006: Handle very long username")
    else:
        results.fail_test("T006: Handle very long username", f"Status {response.status_code}")
except Exception as e:
    results.fail_test("T006: Handle very long username", str(e))

# Test 7: Register with unicode/emoji
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "user_😀_test",
        "password": "🔐password",
        "display_name": "Unicode 你好 User"
    })
    if response.status_code == 201:
        results.pass_test("T007: Handle unicode/emoji")
    else:
        results.pass_test("T007: Reject unicode/emoji")
except Exception as e:
    results.fail_test("T007: Handle unicode/emoji", str(e))

# Test 8: Register with null bytes
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "user\x00null",
        "password": "pass",
        "display_name": "Null"
    })
    if response.status_code in [201, 400]:
        results.pass_test("T008: Handle null bytes")
    else:
        results.fail_test("T008: Handle null bytes", f"Status {response.status_code}")
except Exception as e:
    results.pass_test("T008: Handle null bytes (JSON encode error expected)")

# Test 9: Register with missing fields
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "incomplete"
    })
    if response.status_code == 400:
        results.pass_test("T009: Reject missing required fields")
    else:
        results.fail_test("T009: Reject missing required fields", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T009: Reject missing required fields", str(e))

# Test 10: Register with wrong data types
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": 12345,
        "password": True,
        "display_name": ["array"]
    })
    if response.status_code == 400:
        results.pass_test("T010: Reject wrong data types")
    else:
        results.fail_test("T010: Reject wrong data types", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T010: Reject wrong data types", str(e))

# Test 11: Register with array instead of object
try:
    response = requests.post(f"{BASE_URL}/auth/register", 
        json=["username", "password", "display_name"],
        headers={"Content-Type": "application/json"})
    if response.status_code == 400:
        results.pass_test("T011: Reject array instead of object")
    else:
        results.fail_test("T011: Reject array instead of object", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T011: Reject array instead of object", str(e))

# Test 12: Register with malformed JSON
try:
    response = requests.post(f"{BASE_URL}/auth/register",
        data='{"username": "test", "password": "pass", "display_name": "Test"',
        headers={"Content-Type": "application/json"})
    if response.status_code == 400:
        results.pass_test("T012: Reject malformed JSON")
    else:
        results.fail_test("T012: Reject malformed JSON", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T012: Reject malformed JSON", str(e))

# Test 13: Register without Content-Type header
try:
    response = requests.post(f"{BASE_URL}/auth/register",
        data='{"username": "test", "password": "pass", "display_name": "Test"}')
    if response.status_code in [400, 415]:
        results.pass_test("T013: Reject missing Content-Type")
    else:
        results.fail_test("T013: Reject missing Content-Type", f"Should reject, got {response.status_code}")
except Exception as e:
    results.fail_test("T013: Reject missing Content-Type", str(e))

# Create a valid user for subsequent tests
test_user = f"testuser_{rand_str(8)}"
test_pass = "password123"
test_token = None
test_user_id = None

try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": test_user,
        "password": test_pass,
        "display_name": "Test User"
    })
    if response.status_code == 201:
        data = response.json()
        test_token = data["token"]
        test_user_id = data["user_id"]
except:
    pass

# Test 14: Login with correct credentials
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": test_user,
        "password": test_pass
    })
    if response.status_code == 200:
        results.pass_test("T014: Login with correct credentials")
    else:
        results.fail_test("T014: Login with correct credentials", f"Status {response.status_code}")
except Exception as e:
    results.fail_test("T014: Login with correct credentials", str(e))

# Test 15: Login with wrong password
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": test_user,
        "password": "wrongpassword"
    })
    if response.status_code == 401:
        results.pass_test("T015: Reject wrong password")
    else:
        results.fail_test("T015: Reject wrong password", f"Should be 401, got {response.status_code}")
except Exception as e:
    results.fail_test("T015: Reject wrong password", str(e))

# Test 16: Login with non-existent user
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "nonexistent_user_xyz",
        "password": "password"
    })
    if response.status_code == 401:
        results.pass_test("T016: Reject non-existent user")
    else:
        results.fail_test("T016: Reject non-existent user", f"Should be 401, got {response.status_code}")
except Exception as e:
    results.fail_test("T016: Reject non-existent user", str(e))

# Test 17: Login with extra fields (should fail)
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": test_user,
        "password": test_pass,
        "extra_field": "should_not_be_here"
    })
    if response.status_code == 400:
        results.pass_test("T017: Reject extra fields in login")
    else:
        results.fail_test("T017: Reject extra fields in login", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T017: Reject extra fields in login", str(e))

# Test 18: Case sensitivity in username
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": test_user.upper(),
        "password": test_pass
    })
    if response.status_code == 401:
        results.pass_test("T018: Usernames are case-sensitive")
    elif response.status_code == 200:
        results.pass_test("T018: Usernames are case-insensitive (acceptable)")
    else:
        results.fail_test("T018: Username case sensitivity", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T018: Username case sensitivity", str(e))

# Test 19: Verify user_id format (must start with u_)
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": f"format_test_{rand_str()}",
        "password": "password",
        "display_name": "Format Test"
    })
    if response.status_code == 201:
        data = response.json()
        if data["user_id"].startswith("u_") and len(data["user_id"]) > 2:
            results.pass_test("T019: user_id has correct format")
        else:
            results.fail_test("T019: user_id has correct format", f"Invalid format: {data['user_id']}")
    else:
        results.fail_test("T019: user_id has correct format", "Registration failed")
except Exception as e:
    results.fail_test("T019: user_id has correct format", str(e))

# Test 20: Token is not empty
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": test_user,
        "password": test_pass
    })
    if response.status_code == 200:
        data = response.json()
        if data["token"] and len(data["token"]) > 10:
            results.pass_test("T020: Token is non-empty and substantial")
        else:
            results.fail_test("T020: Token is non-empty and substantial", "Token too short or empty")
    else:
        results.fail_test("T020: Token is non-empty and substantial", "Login failed")
except Exception as e:
    results.fail_test("T020: Token is non-empty and substantial", str(e))

# =============================================================================
# SECTION 2: AUTHORIZATION & SECURITY TESTS (Tests 21-35)
# =============================================================================
print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
print(f"{Colors.YELLOW}SECTION 2: AUTHORIZATION & SECURITY TESTS (15 tests){Colors.END}")
print(f"{Colors.YELLOW}{'='*80}{Colors.END}")

# Test 21: Request without auth token
try:
    response = requests.get(f"{BASE_URL}/user/details")
    if response.status_code == 401:
        results.pass_test("T021: Reject request without auth token")
    else:
        results.fail_test("T021: Reject request without auth token", f"Should be 401, got {response.status_code}")
except Exception as e:
    results.fail_test("T021: Reject request without auth token", str(e))

# Test 22: Request with invalid token
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": "Bearer invalid_token_xyz"})
    if response.status_code == 401:
        results.pass_test("T022: Reject invalid auth token")
    else:
        results.fail_test("T022: Reject invalid auth token", f"Should be 401, got {response.status_code}")
except Exception as e:
    results.fail_test("T022: Reject invalid auth token", str(e))

# Test 23: Request with malformed Authorization header
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": "InvalidFormat token"})
    if response.status_code == 401:
        results.pass_test("T023: Reject malformed Authorization header")
    else:
        results.fail_test("T023: Reject malformed Authorization header", f"Should be 401, got {response.status_code}")
except Exception as e:
    results.fail_test("T023: Reject malformed Authorization header", str(e))

# Test 24: Request with empty Bearer token
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": "Bearer "})
    if response.status_code == 401:
        results.pass_test("T024: Reject empty Bearer token")
    else:
        results.fail_test("T024: Reject empty Bearer token", f"Should be 401, got {response.status_code}")
except Exception as e:
    results.fail_test("T024: Reject empty Bearer token", str(e))

# Test 25: SQL injection in token
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": "Bearer ' OR '1'='1"})
    if response.status_code == 401:
        results.pass_test("T025: Reject SQL injection in token")
    else:
        results.fail_test("T025: Reject SQL injection in token", f"Should be 401, got {response.status_code}")
except Exception as e:
    results.fail_test("T025: Reject SQL injection in token", str(e))

# Test 26: Very long token
try:
    long_token = "a" * 100000
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"Bearer {long_token}"})
    if response.status_code == 401:
        results.pass_test("T026: Handle very long token")
    else:
        results.fail_test("T026: Handle very long token", f"Should be 401, got {response.status_code}")
except Exception as e:
    results.fail_test("T026: Handle very long token", str(e))

# Test 27: Multiple Authorization headers
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers=[
            ("Authorization", f"Bearer {test_token}"),
            ("Authorization", "Bearer fake_token")
        ])
    # Should either work with first valid token or reject multiple headers
    if response.status_code in [200, 400, 401]:
        results.pass_test("T027: Handle multiple Authorization headers")
    else:
        results.fail_test("T027: Handle multiple Authorization headers", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T027: Handle multiple Authorization headers", str(e))

# Test 28: Case-insensitive Bearer keyword
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"bearer {test_token}"})
    if response.status_code in [200, 401]:
        results.pass_test("T028: Handle case variations in Bearer")
    else:
        results.fail_test("T028: Handle case variations in Bearer", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T028: Handle case variations in Bearer", str(e))

# Test 29: Token with extra spaces
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"Bearer   {test_token}   "})
    if response.status_code in [200, 401]:
        results.pass_test("T029: Handle token with extra spaces")
    else:
        results.fail_test("T029: Handle token with extra spaces", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T029: Handle token with extra spaces", str(e))

# Test 30: Access other user's details (should work - public endpoint)
try:
    other_user = f"other_{rand_str()}"
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": other_user,
        "password": "password",
        "display_name": "Other"
    })
    other_user_id = response.json()["user_id"]
    
    response = requests.get(f"{BASE_URL}/user/details?user_id={other_user_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code == 200:
        results.pass_test("T030: Can access other user details")
    else:
        results.fail_test("T030: Can access other user details", f"Should be 200, got {response.status_code}")
except Exception as e:
    results.fail_test("T030: Can access other user details", str(e))

# Test 31: Delete other user's post (should fail)
try:
    # Create a post as test_user
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Test post for deletion")},
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 201:
        post_id = response.json()["post_id"]
        
        # Try to delete with different user
        other_response = requests.post(f"{BASE_URL}/auth/register", json={
            "username": f"attacker_{rand_str()}",
            "password": "password",
            "display_name": "Attacker"
        })
        attacker_token = other_response.json()["token"]
        
        response = requests.post(f"{BASE_URL}/posts/delete",
            json={"post_id": post_id},
            headers={"Authorization": f"Bearer {attacker_token}", "Content-Type": "application/json"})
        
        if response.status_code in [403, 404]:
            results.pass_test("T031: Prevent deleting other user's posts")
        else:
            results.fail_test("T031: Prevent deleting other user's posts", f"Should be 403/404, got {response.status_code}")
except Exception as e:
    results.fail_test("T031: Prevent deleting other user's posts", str(e))

# Test 32: SQL injection in user_id query param
try:
    response = requests.get(f"{BASE_URL}/user/details?user_id=' OR '1'='1",
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code in [404, 400]:
        results.pass_test("T032: Prevent SQL injection in user_id")
    else:
        results.fail_test("T032: Prevent SQL injection in user_id", f"Suspicious status {response.status_code}")
except Exception as e:
    results.fail_test("T032: Prevent SQL injection in user_id", str(e))

# Test 33: XSS in user_id query param
try:
    response = requests.get(f"{BASE_URL}/user/details?user_id=<script>alert('xss')</script>",
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code == 404:
        results.pass_test("T033: Handle XSS in user_id")
    else:
        results.fail_test("T033: Handle XSS in user_id", f"Should be 404, got {response.status_code}")
except Exception as e:
    results.fail_test("T033: Handle XSS in user_id", str(e))

# Test 34: Path traversal attempt
try:
    response = requests.get(f"{BASE_URL}/user/details?user_id=../../etc/passwd",
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code == 404:
        results.pass_test("T034: Prevent path traversal")
    else:
        results.fail_test("T034: Prevent path traversal", f"Should be 404, got {response.status_code}")
except Exception as e:
    results.fail_test("T034: Prevent path traversal", str(e))

# Test 35: Null byte in query param
try:
    response = requests.get(f"{BASE_URL}/user/details?user_id=user\x00admin",
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code == 404:
        results.pass_test("T035: Handle null byte in query param")
    else:
        results.pass_test("T035: Handle null byte in query param (URL encoding)")
except Exception as e:
    results.pass_test("T035: Handle null byte in query param (encoding error expected)")

# =============================================================================
# SECTION 3: REQUEST BODY VALIDATION TESTS (Tests 36-50)
# =============================================================================
print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
print(f"{Colors.YELLOW}SECTION 3: REQUEST BODY VALIDATION TESTS (15 tests){Colors.END}")
print(f"{Colors.YELLOW}{'='*80}{Colors.END}")

# Test 36: GET request with body (should fail)
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"Bearer {test_token}"},
        json={"extra": "data"})
    if response.status_code == 400:
        results.pass_test("T036: Reject GET with body")
    else:
        results.fail_test("T036: Reject GET with body", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T036: Reject GET with body", str(e))

# Test 37: POST /user/delete with non-empty body
try:
    response = requests.post(f"{BASE_URL}/user/delete",
        json={"extra_field": "value"},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    if response.status_code == 400:
        results.pass_test("T037: Reject /user/delete with extra fields")
    else:
        results.fail_test("T037: Reject /user/delete with extra fields", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T037: Reject /user/delete with extra fields", str(e))

# Test 38: POST /user/delete with array body
try:
    temp_user = f"temp_{rand_str()}"
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": temp_user,
        "password": "password",
        "display_name": "Temp"
    })
    temp_token = response.json()["token"]
    
    response = requests.post(f"{BASE_URL}/user/delete",
        json=[],
        headers={"Authorization": f"Bearer {temp_token}", "Content-Type": "application/json"})
    if response.status_code == 400:
        results.pass_test("T038: Reject /user/delete with array")
    else:
        results.fail_test("T038: Reject /user/delete with array", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T038: Reject /user/delete with array", str(e))

# Test 39: POST with null body
try:
    response = requests.post(f"{BASE_URL}/posts/like",
        data='null',
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    if response.status_code == 400:
        results.pass_test("T039: Reject null body")
    else:
        results.fail_test("T039: Reject null body", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T039: Reject null body", str(e))

# Test 40: Extremely large JSON payload
try:
    large_content = "A" * 1000000  # 1MB
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, large_content)},
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code in [201, 413, 400]:
        results.pass_test("T040: Handle large payload")
    else:
        results.fail_test("T040: Handle large payload", f"Unexpected status {response.status_code}")
except Exception as e:
    results.pass_test("T040: Handle large payload (timeout/error expected)")

# Test 41: Deeply nested JSON
try:
    nested = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": {"j": "deep"}}}}}}}}}}
    response = requests.post(f"{BASE_URL}/auth/register",
        json=nested,
        headers={"Content-Type": "application/json"})
    if response.status_code == 400:
        results.pass_test("T041: Reject deeply nested JSON")
    else:
        results.fail_test("T041: Reject deeply nested JSON", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T041: Reject deeply nested JSON", str(e))

# Test 42: JSON with duplicate keys
try:
    response = requests.post(f"{BASE_URL}/auth/register",
        data='{"username":"user1","password":"pass","display_name":"Test","username":"user2"}',
        headers={"Content-Type": "application/json"})
    if response.status_code in [201, 400]:
        results.pass_test("T042: Handle duplicate JSON keys")
    else:
        results.fail_test("T042: Handle duplicate JSON keys", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T042: Handle duplicate JSON keys", str(e))

# Test 43: Invalid UTF-8 in JSON
try:
    response = requests.post(f"{BASE_URL}/auth/register",
        data=b'{"username":"test\xff\xfe","password":"pass","display_name":"Test"}',
        headers={"Content-Type": "application/json"})
    if response.status_code == 400:
        results.pass_test("T043: Reject invalid UTF-8")
    else:
        results.fail_test("T043: Reject invalid UTF-8", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.pass_test("T043: Reject invalid UTF-8 (expected)")

# Test 44: Content-Type charset mismatch
try:
    response = requests.post(f"{BASE_URL}/auth/register",
        data='{"username":"test","password":"pass","display_name":"Test"}'.encode('utf-16'),
        headers={"Content-Type": "application/json; charset=utf-16"})
    if response.status_code in [200, 201, 400, 415]:
        results.pass_test("T044: Handle charset variations")
    else:
        results.fail_test("T044: Handle charset variations", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T044: Handle charset variations", str(e))

# Test 45: Multipart form with wrong Content-Type
try:
    response = requests.post(f"{BASE_URL}/posts/like",
        files={"post_id": (None, "p_123"), "liked": (None, "true")},
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code in [400, 415]:
        results.pass_test("T045: Reject wrong Content-Type for endpoint")
    else:
        results.fail_test("T045: Reject wrong Content-Type for endpoint", f"Should reject, got {response.status_code}")
except Exception as e:
    results.fail_test("T045: Reject wrong Content-Type for endpoint", str(e))

# Test 46-50: Additional body validation tests
test_cases = [
    ("T046", "Integer overflow in limit", lambda: requests.get(
        f"{BASE_URL}/user/get_posts?limit=999999999999999999999",
        headers={"Authorization": f"Bearer {test_token}"})),
    ("T047", "Negative limit", lambda: requests.get(
        f"{BASE_URL}/user/get_posts?limit=-1",
        headers={"Authorization": f"Bearer {test_token}"})),
    ("T048", "Zero limit", lambda: requests.get(
        f"{BASE_URL}/user/get_posts?limit=0",
        headers={"Authorization": f"Bearer {test_token}"})),
    ("T049", "Non-numeric limit", lambda: requests.get(
        f"{BASE_URL}/user/get_posts?limit=abc",
        headers={"Authorization": f"Bearer {test_token}"})),
    ("T050", "Float limit", lambda: requests.get(
        f"{BASE_URL}/user/get_posts?limit=5.5",
        headers={"Authorization": f"Bearer {test_token}"})),
]

for test_id, test_name, test_func in test_cases:
    try:
        response = test_func()
        if response.status_code in [200, 400]:
            results.pass_test(f"{test_id}: {test_name}")
        else:
            results.fail_test(f"{test_id}: {test_name}", f"Status {response.status_code}")
    except Exception as e:
        results.fail_test(f"{test_id}: {test_name}", str(e))

# =============================================================================
# SECTION 4: POST OPERATIONS & CONCURRENCY (Tests 51-65)
# =============================================================================
print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
print(f"{Colors.YELLOW}SECTION 4: POST OPERATIONS & CONCURRENCY (15 tests){Colors.END}")
print(f"{Colors.YELLOW}{'='*80}{Colors.END}")

# Test 51: Create post with empty content
try:
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "")},
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code == 400:
        results.pass_test("T051: Reject empty post content")
    else:
        results.fail_test("T051: Reject empty post content", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T051: Reject empty post content", str(e))

# Test 52: Create post with only whitespace
try:
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "     ")},
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code == 400:
        results.pass_test("T052: Reject whitespace-only content")
    else:
        results.fail_test("T052: Reject whitespace-only content", f"Should be 400, got {response.status_code}")
except Exception as e:
    results.fail_test("T052: Reject whitespace-only content", str(e))

# Test 53: Create comment with non-existent parent
try:
    response = requests.post(f"{BASE_URL}/posts/create",
        files={
            "content": (None, "Orphan comment"),
            "parent_post_id": (None, "p_nonexistent123")
        },
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code in [400, 404]:
        results.pass_test("T053: Reject comment with invalid parent")
    else:
        results.fail_test("T053: Reject comment with invalid parent", f"Should be 400/404, got {response.status_code}")
except Exception as e:
    results.fail_test("T053: Reject comment with invalid parent", str(e))

# Test 54: Create post, verify post_id format
try:
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Format test post")},
        headers={"Authorization": f"Bearer {test_token}"})
    if response.status_code == 201:
        data = response.json()
        if data["post_id"].startswith("p_") and len(data["post_id"]) > 2:
            results.pass_test("T054: post_id has correct format")
        else:
            results.fail_test("T054: post_id has correct format", f"Invalid format: {data['post_id']}")
    else:
        results.fail_test("T054: post_id has correct format", "Post creation failed")
except Exception as e:
    results.fail_test("T054: post_id has correct format", str(e))

# Test 55: Verify created_at is recent
try:
    before = time.time()
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Timestamp test")},
        headers={"Authorization": f"Bearer {test_token}"})
    after = time.time()
    
    if response.status_code == 201:
        data = response.json()
        from datetime import datetime
        created_at = datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        created_timestamp = created_at.timestamp()
        
        if before <= created_timestamp <= after + 5:
            results.pass_test("T055: created_at is accurate")
        else:
            results.fail_test("T055: created_at is accurate", "Timestamp out of range")
    else:
        results.fail_test("T055: created_at is accurate", "Post creation failed")
except Exception as e:
    results.fail_test("T055: created_at is accurate", str(e))

# Test 56: Like non-existent post
try:
    response = requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": "p_nonexistent999", "liked": True},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    if response.status_code == 404:
        results.pass_test("T056: Reject like on non-existent post")
    else:
        results.fail_test("T056: Reject like on non-existent post", f"Should be 404, got {response.status_code}")
except Exception as e:
    results.fail_test("T056: Reject like on non-existent post", str(e))

# Test 57: Like with invalid post_id format
try:
    response = requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": "invalid_id", "liked": True},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    if response.status_code in [400, 404]:
        results.pass_test("T057: Reject invalid post_id format")
    else:
        results.fail_test("T057: Reject invalid post_id format", f"Should be 400/404, got {response.status_code}")
except Exception as e:
    results.fail_test("T057: Reject invalid post_id format", str(e))

# Test 58: Rapid like/unlike toggle
try:
    # Create a post
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Toggle test post")},
        headers={"Authorization": f"Bearer {test_token}"})
    post_id = response.json()["post_id"]
    
    # Rapid toggle
    for i in range(5):
        requests.post(f"{BASE_URL}/posts/like",
            json={"post_id": post_id, "liked": i % 2 == 0},
            headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    # Check final state
    response = requests.get(f"{BASE_URL}/posts/details?post_id={post_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        results.pass_test("T058: Handle rapid like/unlike toggle")
    else:
        results.fail_test("T058: Handle rapid like/unlike toggle", "Failed to verify")
except Exception as e:
    results.fail_test("T058: Handle rapid like/unlike toggle", str(e))

# Test 59: Concurrent likes on same post
try:
    # Create post
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Concurrent like test")},
        headers={"Authorization": f"Bearer {test_token}"})
    post_id = response.json()["post_id"]
    
    # Create multiple users
    users = []
    for i in range(10):
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "username": f"concurrent_{i}_{rand_str()}",
            "password": "pass",
            "display_name": f"User {i}"
        })
        if resp.status_code == 201:
            users.append(resp.json()["token"])
    
    # Like concurrently
    def like_post(token):
        return requests.post(f"{BASE_URL}/posts/like",
            json={"post_id": post_id, "liked": True},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(like_post, token) for token in users]
        concurrent.futures.wait(futures)
    
    # Verify count
    response = requests.get(f"{BASE_URL}/posts/details?post_id={post_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        data = response.json()
        if data["like_count"] == len(users):
            results.pass_test("T059: Concurrent likes accuracy")
        else:
            results.fail_test("T059: Concurrent likes accuracy", f"Expected {len(users)}, got {data['like_count']}")
    else:
        results.fail_test("T059: Concurrent likes accuracy", "Failed to verify")
except Exception as e:
    results.fail_test("T059: Concurrent likes accuracy", str(e))

# Test 60: Double-like idempotency
try:
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Idempotency test")},
        headers={"Authorization": f"Bearer {test_token}"})
    post_id = response.json()["post_id"]
    
    # Like twice
    requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": post_id, "liked": True},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    response = requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": post_id, "liked": True},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    if response.status_code == 200:
        data = response.json()
        if data["like_count"] == 1:
            results.pass_test("T060: Like idempotency")
        else:
            results.fail_test("T060: Like idempotency", f"Count should be 1, got {data['like_count']}")
    else:
        results.fail_test("T060: Like idempotency", "Request failed")
except Exception as e:
    results.fail_test("T060: Like idempotency", str(e))

# Test 61: Unlike without prior like
try:
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Unlike test")},
        headers={"Authorization": f"Bearer {test_token}"})
    post_id = response.json()["post_id"]
    
    response = requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": post_id, "liked": False},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    if response.status_code == 200:
        data = response.json()
        if data["like_count"] == 0:
            results.pass_test("T061: Unlike without prior like")
        else:
            results.fail_test("T061: Unlike without prior like", "Like count should be 0")
    else:
        results.fail_test("T061: Unlike without prior like", "Request failed")
except Exception as e:
    results.fail_test("T061: Unlike without prior like", str(e))

# Test 62: Comment count accuracy
try:
    # Create parent
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Parent post")},
        headers={"Authorization": f"Bearer {test_token}"})
    parent_id = response.json()["post_id"]
    
    # Create 3 direct comments
    for i in range(3):
        requests.post(f"{BASE_URL}/posts/create",
            files={
                "content": (None, f"Comment {i}"),
                "parent_post_id": (None, parent_id)
            },
            headers={"Authorization": f"Bearer {test_token}"})
    
    # Verify count
    response = requests.get(f"{BASE_URL}/posts/details?post_id={parent_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        data = response.json()
        if data["comment_count"] == 3:
            results.pass_test("T062: Comment count accuracy")
        else:
            results.fail_test("T062: Comment count accuracy", f"Expected 3, got {data['comment_count']}")
    else:
        results.fail_test("T062: Comment count accuracy", "Failed to verify")
except Exception as e:
    results.fail_test("T062: Comment count accuracy", str(e))

# Test 63: Nested comments don't affect parent count
try:
    # Create parent
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Grand parent")},
        headers={"Authorization": f"Bearer {test_token}"})
    grandparent_id = response.json()["post_id"]
    
    # Create child
    response = requests.post(f"{BASE_URL}/posts/create",
        files={
            "content": (None, "Parent comment"),
            "parent_post_id": (None, grandparent_id)
        },
        headers={"Authorization": f"Bearer {test_token}"})
    parent_id = response.json()["post_id"]
    
    # Create grandchild
    requests.post(f"{BASE_URL}/posts/create",
        files={
            "content": (None, "Child comment"),
            "parent_post_id": (None, parent_id)
        },
        headers={"Authorization": f"Bearer {test_token}"})
    
    # Verify grandparent count is 1, not 2
    response = requests.get(f"{BASE_URL}/posts/details?post_id={grandparent_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        data = response.json()
        if data["comment_count"] == 1:
            results.pass_test("T063: Nested comments don't double-count")
        else:
            results.fail_test("T063: Nested comments don't double-count", f"Expected 1, got {data['comment_count']}")
    else:
        results.fail_test("T063: Nested comments don't double-count", "Failed to verify")
except Exception as e:
    results.fail_test("T063: Nested comments don't double-count", str(e))

# Test 64: Delete post updates comment_count
try:
    # Create parent
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Delete test parent")},
        headers={"Authorization": f"Bearer {test_token}"})
    parent_id = response.json()["post_id"]
    
    # Create comment
    response = requests.post(f"{BASE_URL}/posts/create",
        files={
            "content": (None, "Comment to delete"),
            "parent_post_id": (None, parent_id)
        },
        headers={"Authorization": f"Bearer {test_token}"})
    comment_id = response.json()["post_id"]
    
    # Delete comment
    requests.post(f"{BASE_URL}/posts/delete",
        json={"post_id": comment_id},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    # Verify parent count decreased
    response = requests.get(f"{BASE_URL}/posts/details?post_id={parent_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        data = response.json()
        if data["comment_count"] == 0:
            results.pass_test("T064: Delete updates comment_count")
        else:
            results.fail_test("T064: Delete updates comment_count", f"Expected 0, got {data['comment_count']}")
    else:
        results.fail_test("T064: Delete updates comment_count", "Failed to verify")
except Exception as e:
    results.fail_test("T064: Delete updates comment_count", str(e))

# Test 65: liked_by_me accuracy
try:
    # Create post
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "liked_by_me test")},
        headers={"Authorization": f"Bearer {test_token}"})
    post_id = response.json()["post_id"]
    
    # Check before like
    response = requests.get(f"{BASE_URL}/posts/details?post_id={post_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.json()["liked_by_me"] == False:
        # Like it
        requests.post(f"{BASE_URL}/posts/like",
            json={"post_id": post_id, "liked": True},
            headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
        
        # Check after like
        response = requests.get(f"{BASE_URL}/posts/details?post_id={post_id}",
            headers={"Authorization": f"Bearer {test_token}"})
        
        if response.json()["liked_by_me"] == True:
            results.pass_test("T065: liked_by_me accuracy")
        else:
            results.fail_test("T065: liked_by_me accuracy", "Should be true after like")
    else:
        results.fail_test("T065: liked_by_me accuracy", "Should be false initially")
except Exception as e:
    results.fail_test("T065: liked_by_me accuracy", str(e))

# =============================================================================
# SECTION 5: PAGINATION STRESS TESTS (Tests 66-75)
# =============================================================================
print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
print(f"{Colors.YELLOW}SECTION 5: PAGINATION STRESS TESTS (10 tests){Colors.END}")
print(f"{Colors.YELLOW}{'='*80}{Colors.END}")

# Test 66: Empty result set has null cursor
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&limit=100",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        data = response.json()
        # If no posts or fewer than limit, next_cursor should be null
        if len(data["posts"]) < 100 and data["next_cursor"] is None:
            results.pass_test("T066: Empty/partial page has null cursor")
        elif len(data["posts"]) == 100 and data["next_cursor"] is not None:
            results.pass_test("T066: Full page has cursor")
        else:
            results.fail_test("T066: Cursor logic", "Cursor doesn't match page fullness")
    else:
        results.fail_test("T066: Cursor logic", "Request failed")
except Exception as e:
    results.fail_test("T066: Cursor logic", str(e))

# Test 67: Create many posts and paginate
try:
    # Create 25 posts
    for i in range(25):
        requests.post(f"{BASE_URL}/posts/create",
            files={"content": (None, f"Pagination test post {i}")},
            headers={"Authorization": f"Bearer {test_token}"})
        time.sleep(0.01)  # Small delay to ensure different timestamps
    
    # Get first page
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&limit=10",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        data = response.json()
        if len(data["posts"]) == 10 and data["next_cursor"] is not None:
            results.pass_test("T067: Pagination first page")
        else:
            results.fail_test("T067: Pagination first page", f"Expected 10 posts and cursor, got {len(data['posts'])}")
    else:
        results.fail_test("T067: Pagination first page", "Request failed")
except Exception as e:
    results.fail_test("T067: Pagination first page", str(e))

# Test 68: Follow cursor to next page
try:
    response1 = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&limit=10",
        headers={"Authorization": f"Bearer {test_token}"})
    cursor = response1.json()["next_cursor"]
    
    response2 = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&limit=10&cursor={cursor}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response2.status_code == 200:
        data1 = response1.json()["posts"]
        data2 = response2.json()["posts"]
        
        # Check no overlap
        ids1 = {p["post_id"] for p in data1}
        ids2 = {p["post_id"] for p in data2}
        
        if len(ids1 & ids2) == 0:
            results.pass_test("T068: Cursor pagination no overlap")
        else:
            results.fail_test("T068: Cursor pagination no overlap", "Pages have overlapping posts")
    else:
        results.fail_test("T068: Cursor pagination no overlap", "Request failed")
except Exception as e:
    results.fail_test("T068: Cursor pagination no overlap", str(e))

# Test 69: Invalid cursor format
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&cursor=invalid_cursor",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code in [200, 400]:
        results.pass_test("T069: Handle invalid cursor")
    else:
        results.fail_test("T069: Handle invalid cursor", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T069: Handle invalid cursor", str(e))

# Test 70: Tampered cursor (base64 decode to random data)
try:
    fake_cursor = base64.urlsafe_b64encode(b"2026-01-01T00:00:00Z|p_fake").decode()
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&cursor={fake_cursor}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code in [200, 400]:
        results.pass_test("T070: Handle tampered cursor")
    else:
        results.fail_test("T070: Handle tampered cursor", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T070: Handle tampered cursor", str(e))

# Test 71: SQL injection in cursor
try:
    malicious_cursor = base64.urlsafe_b64encode(b"' OR '1'='1|p_123").decode()
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&cursor={malicious_cursor}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code in [200, 400]:
        results.pass_test("T071: Prevent SQL injection in cursor")
    else:
        results.fail_test("T071: Prevent SQL injection in cursor", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T071: Prevent SQL injection in cursor", str(e))

# Test 72: Pagination order (newest first)
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&limit=5",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        posts = response.json()["posts"]
        if len(posts) >= 2:
            from datetime import datetime
            timestamps = [datetime.fromisoformat(p["created_at"].replace('Z', '+00:00')) for p in posts]
            is_sorted = all(timestamps[i] >= timestamps[i+1] for i in range(len(timestamps)-1))
            
            if is_sorted:
                results.pass_test("T072: Posts ordered newest first")
            else:
                results.fail_test("T072: Posts ordered newest first", "Order incorrect")
        else:
            results.pass_test("T072: Posts ordered newest first (insufficient data)")
    else:
        results.fail_test("T072: Posts ordered newest first", "Request failed")
except Exception as e:
    results.fail_test("T072: Posts ordered newest first", str(e))

# Test 73: Limit beyond available posts
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&limit=1000",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        data = response.json()
        # Should return all available posts, cursor should be null
        if data["next_cursor"] is None:
            results.pass_test("T073: Limit beyond available posts")
        else:
            results.fail_test("T073: Limit beyond available posts", "Cursor should be null")
    else:
        results.fail_test("T073: Limit beyond available posts", "Request failed")
except Exception as e:
    results.fail_test("T073: Limit beyond available posts", str(e))

# Test 74: liked_posts pagination
try:
    # Like several posts
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&limit=5",
        headers={"Authorization": f"Bearer {test_token}"})
    posts = response.json()["posts"]
    
    for post in posts[:3]:
        requests.post(f"{BASE_URL}/posts/like",
            json={"post_id": post["post_id"], "liked": True},
            headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    # Get liked posts
    response = requests.get(f"{BASE_URL}/user/liked_posts?user_id={test_user_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        data = response.json()
        if all(p["liked_by_me"] == True for p in data["posts"]):
            results.pass_test("T074: liked_posts pagination")
        else:
            results.fail_test("T074: liked_posts pagination", "Not all posts are liked")
    else:
        results.fail_test("T074: liked_posts pagination", "Request failed")
except Exception as e:
    results.fail_test("T074: liked_posts pagination", str(e))

# Test 75: Concurrent pagination reads
try:
    def get_page(offset):
        response = requests.get(f"{BASE_URL}/user/get_posts?user_id={test_user_id}&limit=5",
            headers={"Authorization": f"Bearer {test_token}"})
        return response.json()["posts"] if response.status_code == 200 else []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(get_page, i) for i in range(5)]
        results_list = [f.result() for f in futures]
    
    # All should return same first page
    if all(len(r) > 0 for r in results_list):
        results.pass_test("T075: Concurrent pagination reads")
    else:
        results.fail_test("T075: Concurrent pagination reads", "Some requests failed")
except Exception as e:
    results.fail_test("T075: Concurrent pagination reads", str(e))

# =============================================================================
# SECTION 6: EXTREME EDGE CASES (Tests 76-85)
# =============================================================================
print(f"\n{Colors.YELLOW}{'='*80}{Colors.END}")
print(f"{Colors.YELLOW}SECTION 6: EXTREME EDGE CASES (10 tests){Colors.END}")
print(f"{Colors.YELLOW}{'='*80}{Colors.END}")

# Test 76: User deletion cascades
try:
    # Create temp user
    temp_user = f"cascade_{rand_str()}"
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": temp_user,
        "password": "password",
        "display_name": "Cascade Test"
    })
    temp_token = response.json()["token"]
    temp_user_id = response.json()["user_id"]
    
    # Create posts
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Post to cascade delete")},
        headers={"Authorization": f"Bearer {temp_token}"})
    post_id = response.json()["post_id"]
    
    # Delete user
    requests.post(f"{BASE_URL}/user/delete",
        json={},
        headers={"Authorization": f"Bearer {temp_token}", "Content-Type": "application/json"})
    
    # Try to access post (should fail)
    response = requests.get(f"{BASE_URL}/posts/details?post_id={post_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 404:
        results.pass_test("T076: User deletion cascades to posts")
    else:
        results.fail_test("T076: User deletion cascades to posts", "Post still exists")
except Exception as e:
    results.fail_test("T076: User deletion cascades to posts", str(e))

# Test 77: Post deletion cascades to likes
try:
    # Create post
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Like cascade test")},
        headers={"Authorization": f"Bearer {test_token}"})
    post_id = response.json()["post_id"]
    
    # Like it
    requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": post_id, "liked": True},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    # Delete post
    requests.post(f"{BASE_URL}/posts/delete",
        json={"post_id": post_id},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    # Check liked_posts (should not include deleted post)
    response = requests.get(f"{BASE_URL}/user/liked_posts?user_id={test_user_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 200:
        posts = response.json()["posts"]
        if not any(p["post_id"] == post_id for p in posts):
            results.pass_test("T077: Post deletion cascades to likes")
        else:
            results.fail_test("T077: Post deletion cascades to likes", "Deleted post still in liked_posts")
    else:
        results.fail_test("T077: Post deletion cascades to likes", "Request failed")
except Exception as e:
    results.fail_test("T077: Post deletion cascades to likes", str(e))

# Test 78: Race condition - simultaneous user creation
try:
    base_username = f"race_{rand_str()}"
    
    def register_user():
        return requests.post(f"{BASE_URL}/auth/register", json={
            "username": base_username,
            "password": "password",
            "display_name": "Race"
        })
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(register_user) for _ in range(3)]
        responses = [f.result() for f in futures]
    
    # Exactly one should succeed (201), others should conflict (409)
    success_count = sum(1 for r in responses if r.status_code == 201)
    conflict_count = sum(1 for r in responses if r.status_code == 409)
    
    if success_count == 1 and conflict_count == 2:
        results.pass_test("T078: Race condition - duplicate username")
    else:
        results.fail_test("T078: Race condition - duplicate username", 
            f"Success: {success_count}, Conflicts: {conflict_count}")
except Exception as e:
    results.fail_test("T078: Race condition - duplicate username", str(e))

# Test 79: Orphaned comments (parent deleted)
try:
    # Create parent
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Parent to delete")},
        headers={"Authorization": f"Bearer {test_token}"})
    parent_id = response.json()["post_id"]
    
    # Create comment
    response = requests.post(f"{BASE_URL}/posts/create",
        files={
            "content": (None, "Orphan comment"),
            "parent_post_id": (None, parent_id)
        },
        headers={"Authorization": f"Bearer {test_token}"})
    comment_id = response.json()["post_id"]
    
    # Delete parent
    requests.post(f"{BASE_URL}/posts/delete",
        json={"post_id": parent_id},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    # Try to access comment (behavior varies - could be deleted or orphaned)
    response = requests.get(f"{BASE_URL}/posts/details?post_id={comment_id}",
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code in [200, 404]:
        results.pass_test("T079: Handle orphaned comments")
    else:
        results.fail_test("T079: Handle orphaned comments", f"Unexpected status {response.status_code}")
except Exception as e:
    results.fail_test("T079: Handle orphaned comments", str(e))

# Test 80: post_count accuracy after deletions
try:
    # Get initial count
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"Bearer {test_token}"})
    initial_count = response.json()["post_count"]
    
    # Create post
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Count test post")},
        headers={"Authorization": f"Bearer {test_token}"})
    post_id = response.json()["post_id"]
    
    # Check count increased
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"Bearer {test_token}"})
    after_create = response.json()["post_count"]
    
    # Delete post
    requests.post(f"{BASE_URL}/posts/delete",
        json={"post_id": post_id},
        headers={"Authorization": f"Bearer {test_token}", "Content-Type": "application/json"})
    
    # Check count decreased
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"Bearer {test_token}"})
    after_delete = response.json()["post_count"]
    
    if after_create == initial_count + 1 and after_delete == initial_count:
        results.pass_test("T080: post_count accuracy with deletions")
    else:
        results.fail_test("T080: post_count accuracy with deletions", 
            f"Initial: {initial_count}, After create: {after_create}, After delete: {after_delete}")
except Exception as e:
    results.fail_test("T080: post_count accuracy with deletions", str(e))

# Test 81: Massive concurrent writes
try:
    def create_random_post():
        return requests.post(f"{BASE_URL}/posts/create",
            files={"content": (None, f"Stress test {rand_str()}")},
            headers={"Authorization": f"Bearer {test_token}"})
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(create_random_post) for _ in range(50)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    success_count = sum(1 for r in responses if r.status_code == 201)
    
    if success_count >= 45:  # Allow some failures under extreme load
        results.pass_test("T081: Massive concurrent writes")
    else:
        results.fail_test("T081: Massive concurrent writes", f"Only {success_count}/50 succeeded")
except Exception as e:
    results.fail_test("T081: Massive concurrent writes", str(e))

# Test 82: Special characters in content
try:
    special_content = "Test with special chars: <>&\"'`!@#$%^&*(){}[]|\\:;,.<>?/~"
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, special_content)},
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 201:
        post_id = response.json()["post_id"]
        
        # Verify content preserved
        response = requests.get(f"{BASE_URL}/posts/details?post_id={post_id}",
            headers={"Authorization": f"Bearer {test_token}"})
        
        if response.json()["content"] == special_content:
            results.pass_test("T082: Special characters preserved")
        else:
            results.fail_test("T082: Special characters preserved", "Content corrupted")
    else:
        results.fail_test("T082: Special characters preserved", "Post creation failed")
except Exception as e:
    results.fail_test("T082: Special characters preserved", str(e))

# Test 83: Newlines and formatting in content
try:
    multiline_content = "Line 1\nLine 2\r\nLine 3\tTabbed"
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, multiline_content)},
        headers={"Authorization": f"Bearer {test_token}"})
    
    if response.status_code == 201:
        post_id = response.json()["post_id"]
        
        response = requests.get(f"{BASE_URL}/posts/details?post_id={post_id}",
            headers={"Authorization": f"Bearer {test_token}"})
        
        if response.json()["content"] == multiline_content:
            results.pass_test("T083: Whitespace/newlines preserved")
        else:
            results.fail_test("T083: Whitespace/newlines preserved", "Formatting lost")
    else:
        results.fail_test("T083: Whitespace/newlines preserved", "Post creation failed")
except Exception as e:
    results.fail_test("T083: Whitespace/newlines preserved", str(e))

# Test 84: Very rapid requests from same user
try:
    def rapid_request():
        return requests.get(f"{BASE_URL}/user/details",
            headers={"Authorization": f"Bearer {test_token}"})
    
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(rapid_request) for _ in range(100)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]
    duration = time.time() - start
    
    success_count = sum(1 for r in responses if r.status_code == 200)
    
    if success_count >= 95:
        results.pass_test(f"T084: Rapid requests ({success_count}/100 in {duration:.2f}s)")
    else:
        results.fail_test("T084: Rapid requests", f"Only {success_count}/100 succeeded")
except Exception as e:
    results.fail_test("T084: Rapid requests", str(e))

# Test 85: Response time consistency
try:
    times = []
    for _ in range(10):
        start = time.time()
        requests.get(f"{BASE_URL}/user/details",
            headers={"Authorization": f"Bearer {test_token}"})
        times.append(time.time() - start)
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    
    if max_time < avg_time * 5:  # No request takes more than 5x average
        results.pass_test(f"T085: Response time consistency (avg: {avg_time*1000:.0f}ms)")
    else:
        results.fail_test("T085: Response time consistency", f"High variance: avg {avg_time:.2f}s, max {max_time:.2f}s")
except Exception as e:
    results.fail_test("T085: Response time consistency", str(e))

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print(f"\n{Colors.MAGENTA}{'='*80}{Colors.END}")
print(f"{Colors.MAGENTA}TEST SUITE COMPLETE{Colors.END}")
print(f"{Colors.MAGENTA}{'='*80}{Colors.END}")

success = results.summary()

if success:
    print(f"\n{Colors.GREEN}🎉 ALL TESTS PASSED! Your backend is solid! 🎉{Colors.END}")
else:
    print(f"\n{Colors.RED}⚠️  CRITICAL ISSUES FOUND - Review failures above{Colors.END}")

sys.exit(0 if success else 1)