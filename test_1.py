#!/usr/bin/env python3
"""
Backend Optimizer API Test Suite
Comprehensive testing following the exact specification
"""

import requests
import json
import time
import hashlib
from typing import Dict, Optional, List
import sys

BASE_URL = "http://localhost:8080"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def pass_test(self, name: str):
        self.passed += 1
        print(f"{Colors.GREEN}✓{Colors.END} {name}")
    
    def fail_test(self, name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        print(f"{Colors.RED}✗{Colors.END} {name}: {reason}")
    
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"Total Tests: {total}")
        print(f"{Colors.GREEN}Passed: {self.passed}{Colors.END}")
        print(f"{Colors.RED}Failed: {self.failed}{Colors.END}")
        if self.errors:
            print(f"\n{Colors.RED}Errors:{Colors.END}")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{Colors.BLUE}{'='*60}{Colors.END}")
        return self.failed == 0

results = TestResults()

def assert_status(response: requests.Response, expected: int, test_name: str):
    if response.status_code != expected:
        results.fail_test(test_name, f"Expected status {expected}, got {response.status_code}")
        return False
    return True

def assert_json(response: requests.Response, test_name: str) -> Optional[Dict]:
    try:
        content_type = response.headers.get('Content-Type', '')
        if 'application/json' not in content_type:
            results.fail_test(test_name, f"Expected Content-Type: application/json, got {content_type}")
            return None
        return response.json()
    except Exception as e:
        results.fail_test(test_name, f"Failed to parse JSON: {str(e)}")
        return None

def assert_field(data: Dict, field: str, test_name: str, expected_type=None) -> bool:
    if field not in data:
        results.fail_test(test_name, f"Missing field: {field}")
        return False
    if expected_type and not isinstance(data[field], expected_type):
        results.fail_test(test_name, f"Field {field} has wrong type. Expected {expected_type}, got {type(data[field])}")
        return False
    return True

print(f"{Colors.BLUE}Backend Optimizer API Test Suite{Colors.END}\n")

# Test 1: POST /auth/register - Valid Registration
print(f"\n{Colors.YELLOW}=== Authentication Tests ==={Colors.END}")
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "alice",
        "password": "password123",
        "display_name": "Alice"
    }, headers={"Content-Type": "application/json"})
    
    if assert_status(response, 201, "POST /auth/register - Valid"):
        data = assert_json(response, "POST /auth/register - Valid")
        if data:
            if (assert_field(data, "user_id", "POST /auth/register - user_id", str) and
                assert_field(data, "username", "POST /auth/register - username", str) and
                assert_field(data, "display_name", "POST /auth/register - display_name", str) and
                assert_field(data, "token", "POST /auth/register - token", str)):
                
                if data["username"] == "alice" and data["display_name"] == "Alice":
                    if data["user_id"].startswith("u_"):
                        results.pass_test("POST /auth/register - Valid")
                        alice_token = data["token"]
                        alice_id = data["user_id"]
                    else:
                        results.fail_test("POST /auth/register - Valid", "user_id doesn't start with 'u_'")
                else:
                    results.fail_test("POST /auth/register - Valid", "username or display_name mismatch")
except Exception as e:
    results.fail_test("POST /auth/register - Valid", str(e))

# Test 2: POST /auth/register - Duplicate Username
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "alice",
        "password": "different",
        "display_name": "Alice2"
    }, headers={"Content-Type": "application/json"})
    
    if assert_status(response, 409, "POST /auth/register - Duplicate"):
        data = assert_json(response, "POST /auth/register - Duplicate")
        if data and "error" in data and data["error"] == "user_exists":
            results.pass_test("POST /auth/register - Duplicate")
        else:
            results.fail_test("POST /auth/register - Duplicate", "Wrong error message")
except Exception as e:
    results.fail_test("POST /auth/register - Duplicate", str(e))

# Test 3: POST /auth/register - Extra Fields Rejection
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "bob",
        "password": "pass",
        "display_name": "Bob",
        "extra_field": "should_fail"
    }, headers={"Content-Type": "application/json"})
    
    if assert_status(response, 400, "POST /auth/register - Extra Fields"):
        results.pass_test("POST /auth/register - Extra Fields")
except Exception as e:
    results.fail_test("POST /auth/register - Extra Fields", str(e))

# Test 4: POST /auth/login - Valid Login
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "alice",
        "password": "password123"
    }, headers={"Content-Type": "application/json"})
    
    if assert_status(response, 200, "POST /auth/login - Valid"):
        data = assert_json(response, "POST /auth/login - Valid")
        if data:
            if (assert_field(data, "user_id", "POST /auth/login - user_id", str) and
                assert_field(data, "token", "POST /auth/login - token", str)):
                if data["user_id"] == alice_id:
                    results.pass_test("POST /auth/login - Valid")
                    alice_token = data["token"]
                else:
                    results.fail_test("POST /auth/login - Valid", "user_id mismatch")
except Exception as e:
    results.fail_test("POST /auth/login - Valid", str(e))

# Test 5: POST /auth/login - Wrong Password
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "alice",
        "password": "wrongpassword"
    }, headers={"Content-Type": "application/json"})
    
    if assert_status(response, 401, "POST /auth/login - Wrong Password"):
        data = assert_json(response, "POST /auth/login - Wrong Password")
        if data and "error" in data and data["error"] == "unauthorized":
            results.pass_test("POST /auth/login - Wrong Password")
except Exception as e:
    results.fail_test("POST /auth/login - Wrong Password", str(e))

# Test 6: POST /auth/login - Non-existent User
try:
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "nonexistent",
        "password": "password"
    }, headers={"Content-Type": "application/json"})
    
    if assert_status(response, 401, "POST /auth/login - Non-existent User"):
        results.pass_test("POST /auth/login - Non-existent User")
except Exception as e:
    results.fail_test("POST /auth/login - Non-existent User", str(e))

# Register another user for testing
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "bob",
        "password": "bobpass",
        "display_name": "Bob"
    })
    bob_data = response.json()
    bob_token = bob_data["token"]
    bob_id = bob_data["user_id"]
except:
    bob_token = None
    bob_id = None

print(f"\n{Colors.YELLOW}=== User Management Tests ==={Colors.END}")

# Test 7: GET /user/details - Own Profile
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "GET /user/details - Own Profile"):
        data = assert_json(response, "GET /user/details - Own Profile")
        if data:
            if (assert_field(data, "user_id", "GET /user/details - user_id", str) and
                assert_field(data, "username", "GET /user/details - username", str) and
                assert_field(data, "display_name", "GET /user/details - display_name", str) and
                assert_field(data, "post_count", "GET /user/details - post_count", int)):
                
                if data["username"] == "alice" and data["post_count"] == 0:
                    results.pass_test("GET /user/details - Own Profile")
                else:
                    results.fail_test("GET /user/details - Own Profile", "Data mismatch")
except Exception as e:
    results.fail_test("GET /user/details - Own Profile", str(e))

# Test 8: GET /user/details - Other User Profile
try:
    response = requests.get(f"{BASE_URL}/user/details?user_id={bob_id}",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "GET /user/details - Other User"):
        data = assert_json(response, "GET /user/details - Other User")
        if data and data["username"] == "bob":
            results.pass_test("GET /user/details - Other User")
except Exception as e:
    results.fail_test("GET /user/details - Other User", str(e))

# Test 9: GET /user/details - With Body (should fail)
try:
    response = requests.get(f"{BASE_URL}/user/details",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"extra": "data"})
    
    if assert_status(response, 400, "GET /user/details - Body Rejection"):
        results.pass_test("GET /user/details - Body Rejection")
except Exception as e:
    results.fail_test("GET /user/details - Body Rejection", str(e))

# Test 10: GET /user/details - No Auth
try:
    response = requests.get(f"{BASE_URL}/user/details")
    
    if assert_status(response, 401, "GET /user/details - No Auth"):
        results.pass_test("GET /user/details - No Auth")
except Exception as e:
    results.fail_test("GET /user/details - No Auth", str(e))

print(f"\n{Colors.YELLOW}=== Post Creation Tests ==={Colors.END}")

# Test 11: POST /posts/create - Simple Text Post
try:
    post_content = "Hello world, this is my first post!"
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, post_content)},
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 201, "POST /posts/create - Text Post"):
        data = assert_json(response, "POST /posts/create - Text Post")
        if data:
            if (assert_field(data, "post_id", "POST /posts/create - post_id", str) and
                assert_field(data, "author_id", "POST /posts/create - author_id", str) and
                assert_field(data, "content", "POST /posts/create - content", str) and
                assert_field(data, "created_at", "POST /posts/create - created_at", str)):
                
                if data["post_id"].startswith("p_") and data["author_id"] == alice_id:
                    results.pass_test("POST /posts/create - Text Post")
                    alice_post_id = data["post_id"]
                else:
                    results.fail_test("POST /posts/create - Text Post", "ID format or author mismatch")
except Exception as e:
    results.fail_test("POST /posts/create - Text Post", str(e))

# Test 12: POST /posts/create - Comment (with parent_post_id)
try:
    response = requests.post(f"{BASE_URL}/posts/create",
        files={
            "content": (None, "This is a comment!"),
            "parent_post_id": (None, alice_post_id)
        },
        headers={"Authorization": f"Bearer {bob_token}"})
    
    if assert_status(response, 201, "POST /posts/create - Comment"):
        data = assert_json(response, "POST /posts/create - Comment")
        if data:
            if assert_field(data, "parent_post_id", "POST /posts/create - parent_post_id"):
                if data["parent_post_id"] == alice_post_id:
                    results.pass_test("POST /posts/create - Comment")
                    comment_id = data["post_id"]
except Exception as e:
    results.fail_test("POST /posts/create - Comment", str(e))

# Test 13: POST /posts/create - No Auth
try:
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Unauthorized post")})
    
    if assert_status(response, 401, "POST /posts/create - No Auth"):
        results.pass_test("POST /posts/create - No Auth")
except Exception as e:
    results.fail_test("POST /posts/create - No Auth", str(e))

print(f"\n{Colors.YELLOW}=== Post Retrieval Tests ==={Colors.END}")

# Test 14: GET /posts/details - Valid Post
try:
    response = requests.get(f"{BASE_URL}/posts/details?post_id={alice_post_id}",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "GET /posts/details - Valid"):
        data = assert_json(response, "GET /posts/details - Valid")
        if data:
            if (assert_field(data, "post_id", "GET /posts/details - post_id", str) and
                assert_field(data, "like_count", "GET /posts/details - like_count", int) and
                assert_field(data, "comment_count", "GET /posts/details - comment_count", int) and
                assert_field(data, "liked_by_me", "GET /posts/details - liked_by_me", bool)):
                
                if data["comment_count"] == 1:  # We created 1 comment
                    results.pass_test("GET /posts/details - Valid")
                else:
                    results.fail_test("GET /posts/details - Valid", f"Expected comment_count=1, got {data['comment_count']}")
except Exception as e:
    results.fail_test("GET /posts/details - Valid", str(e))

# Test 15: GET /posts/details - With Body (should fail)
try:
    response = requests.get(f"{BASE_URL}/posts/details?post_id={alice_post_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
        json={"extra": "data"})
    
    if assert_status(response, 400, "GET /posts/details - Body Rejection"):
        results.pass_test("GET /posts/details - Body Rejection")
except Exception as e:
    results.fail_test("GET /posts/details - Body Rejection", str(e))

# Test 16: GET /user/get_posts - User Posts
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={alice_id}",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "GET /user/get_posts - Valid"):
        data = assert_json(response, "GET /user/get_posts - Valid")
        if data:
            if (assert_field(data, "posts", "GET /user/get_posts - posts", list) and
                "next_cursor" in data):
                
                if len(data["posts"]) == 1 and data["posts"][0]["post_id"] == alice_post_id:
                    results.pass_test("GET /user/get_posts - Valid")
                else:
                    results.fail_test("GET /user/get_posts - Valid", "Post data mismatch")
except Exception as e:
    results.fail_test("GET /user/get_posts - Valid", str(e))

# Test 17: GET /user/get_posts - With Limit
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={alice_id}&limit=5",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "GET /user/get_posts - With Limit"):
        data = assert_json(response, "GET /user/get_posts - With Limit")
        if data and len(data["posts"]) <= 5:
            results.pass_test("GET /user/get_posts - With Limit")
except Exception as e:
    results.fail_test("GET /user/get_posts - With Limit", str(e))

# Test 18: GET /user/get_posts - Invalid Limit (should use default)
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={alice_id}&limit=200",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "GET /user/get_posts - Invalid Limit"):
        results.pass_test("GET /user/get_posts - Invalid Limit")
except Exception as e:
    results.fail_test("GET /user/get_posts - Invalid Limit", str(e))

print(f"\n{Colors.YELLOW}=== Like/Unlike Tests ==={Colors.END}")

# Test 19: POST /posts/like - Like a Post
try:
    response = requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": alice_post_id, "liked": True},
        headers={
            "Authorization": f"Bearer {bob_token}",
            "Content-Type": "application/json"
        })
    
    if assert_status(response, 200, "POST /posts/like - Like"):
        data = assert_json(response, "POST /posts/like - Like")
        if data:
            if (assert_field(data, "post_id", "POST /posts/like - post_id", str) and
                assert_field(data, "like_count", "POST /posts/like - like_count", int) and
                assert_field(data, "liked_by_me", "POST /posts/like - liked_by_me", bool)):
                
                if data["like_count"] == 1 and data["liked_by_me"] == True:
                    results.pass_test("POST /posts/like - Like")
                else:
                    results.fail_test("POST /posts/like - Like", "Like count or status mismatch")
except Exception as e:
    results.fail_test("POST /posts/like - Like", str(e))

# Test 20: POST /posts/like - Unlike a Post
try:
    response = requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": alice_post_id, "liked": False},
        headers={
            "Authorization": f"Bearer {bob_token}",
            "Content-Type": "application/json"
        })
    
    if assert_status(response, 200, "POST /posts/like - Unlike"):
        data = assert_json(response, "POST /posts/like - Unlike")
        if data and data["like_count"] == 0 and data["liked_by_me"] == False:
            results.pass_test("POST /posts/like - Unlike")
except Exception as e:
    results.fail_test("POST /posts/like - Unlike", str(e))

# Test 21: POST /posts/like - Like Again (idempotency)
try:
    requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": alice_post_id, "liked": True},
        headers={
            "Authorization": f"Bearer {bob_token}",
            "Content-Type": "application/json"
        })
    
    response = requests.post(f"{BASE_URL}/posts/like",
        json={"post_id": alice_post_id, "liked": True},
        headers={
            "Authorization": f"Bearer {bob_token}",
            "Content-Type": "application/json"
        })
    
    if assert_status(response, 200, "POST /posts/like - Idempotency"):
        data = assert_json(response, "POST /posts/like - Idempotency")
        if data and data["like_count"] == 1:
            results.pass_test("POST /posts/like - Idempotency")
except Exception as e:
    results.fail_test("POST /posts/like - Idempotency", str(e))

# Test 22: GET /user/liked_posts - Liked Posts List
try:
    response = requests.get(f"{BASE_URL}/user/liked_posts?user_id={bob_id}",
        headers={"Authorization": f"Bearer {bob_token}"})
    
    if assert_status(response, 200, "GET /user/liked_posts - Valid"):
        data = assert_json(response, "GET /user/liked_posts - Valid")
        if data:
            if assert_field(data, "posts", "GET /user/liked_posts - posts", list):
                if len(data["posts"]) == 1 and data["posts"][0]["liked_by_me"] == True:
                    results.pass_test("GET /user/liked_posts - Valid")
                else:
                    results.fail_test("GET /user/liked_posts - Valid", "Liked posts mismatch")
except Exception as e:
    results.fail_test("GET /user/liked_posts - Valid", str(e))

# Test 23: GET /user/liked_posts - With Body (should fail)
try:
    response = requests.get(f"{BASE_URL}/user/liked_posts?user_id={bob_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
        json={"extra": "data"})
    
    if assert_status(response, 400, "GET /user/liked_posts - Body Rejection"):
        results.pass_test("GET /user/liked_posts - Body Rejection")
except Exception as e:
    results.fail_test("GET /user/liked_posts - Body Rejection", str(e))

print(f"\n{Colors.YELLOW}=== Post Deletion Tests ==={Colors.END}")

# Test 24: POST /posts/delete - Valid Deletion
try:
    # Create a post to delete
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Post to delete")},
        headers={"Authorization": f"Bearer {alice_token}"})
    delete_post_id = response.json()["post_id"]
    
    response = requests.post(f"{BASE_URL}/posts/delete",
        json={"post_id": delete_post_id},
        headers={
            "Authorization": f"Bearer {alice_token}",
            "Content-Type": "application/json"
        })
    
    if assert_status(response, 200, "POST /posts/delete - Valid"):
        data = assert_json(response, "POST /posts/delete - Valid")
        if data and data.get("success") == True:
            results.pass_test("POST /posts/delete - Valid")
except Exception as e:
    results.fail_test("POST /posts/delete - Valid", str(e))

# Test 25: POST /posts/delete - Non-owner Deletion
try:
    response = requests.post(f"{BASE_URL}/posts/delete",
        json={"post_id": alice_post_id},
        headers={
            "Authorization": f"Bearer {bob_token}",
            "Content-Type": "application/json"
        })
    
    if response.status_code in [403, 404]:
        results.pass_test("POST /posts/delete - Non-owner")
except Exception as e:
    results.fail_test("POST /posts/delete - Non-owner", str(e))

print(f"\n{Colors.YELLOW}=== Pagination Tests ==={Colors.END}")

# Test 26: Pagination - Create Multiple Posts
try:
    for i in range(5):
        requests.post(f"{BASE_URL}/posts/create",
            files={"content": (None, f"Test post {i}")},
            headers={"Authorization": f"Bearer {alice_token}"})
    
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={alice_id}&limit=3",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "Pagination - First Page"):
        data = assert_json(response, "Pagination - First Page")
        if data:
            if len(data["posts"]) == 3 and data["next_cursor"] is not None:
                results.pass_test("Pagination - First Page")
                cursor = data["next_cursor"]
            else:
                results.fail_test("Pagination - First Page", "Wrong number of posts or no cursor")
except Exception as e:
    results.fail_test("Pagination - First Page", str(e))

# Test 27: Pagination - Next Page
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={alice_id}&limit=3&cursor={cursor}",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "Pagination - Next Page"):
        data = assert_json(response, "Pagination - Next Page")
        if data and len(data["posts"]) > 0:
            results.pass_test("Pagination - Next Page")
except Exception as e:
    results.fail_test("Pagination - Next Page", str(e))

# Test 28: Pagination - Last Page (no next_cursor)
try:
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={alice_id}&limit=100",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    if assert_status(response, 200, "Pagination - Last Page"):
        data = assert_json(response, "Pagination - Last Page")
        if data and data["next_cursor"] is None:
            results.pass_test("Pagination - Last Page")
        else:
            results.fail_test("Pagination - Last Page", "Should not have next_cursor")
except Exception as e:
    results.fail_test("Pagination - Last Page", str(e))

print(f"\n{Colors.YELLOW}=== User Deletion Tests ==={Colors.END}")

# Test 29: POST /user/delete - Valid Empty Body
try:
    # Create a user to delete
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "charlie",
        "password": "charliepass",
        "display_name": "Charlie"
    })
    charlie_token = response.json()["token"]
    
    response = requests.post(f"{BASE_URL}/user/delete",
        json={},
        headers={
            "Authorization": f"Bearer {charlie_token}",
            "Content-Type": "application/json"
        })
    
    if assert_status(response, 200, "POST /user/delete - Valid"):
        data = assert_json(response, "POST /user/delete - Valid")
        if data and data.get("success") == True:
            results.pass_test("POST /user/delete - Valid")
except Exception as e:
    results.fail_test("POST /user/delete - Valid", str(e))

# Test 30: POST /user/delete - With Extra Fields
try:
    response = requests.post(f"{BASE_URL}/user/delete",
        json={"extra": "field"},
        headers={
            "Authorization": f"Bearer {alice_token}",
            "Content-Type": "application/json"
        })
    
    if assert_status(response, 400, "POST /user/delete - Extra Fields"):
        results.pass_test("POST /user/delete - Extra Fields")
except Exception as e:
    results.fail_test("POST /user/delete - Extra Fields", str(e))

print(f"\n{Colors.YELLOW}=== Concurrency Tests ==={Colors.END}")

# Test 31: Concurrent Likes
import concurrent.futures

try:
    # Create a post for concurrent testing
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Concurrent test post")},
        headers={"Authorization": f"Bearer {alice_token}"})
    concurrent_post_id = response.json()["post_id"]
    
    # Create multiple users
    user_tokens = []
    for i in range(10):
        response = requests.post(f"{BASE_URL}/auth/register", json={
            "username": f"concurrent_user_{i}",
            "password": "pass",
            "display_name": f"User {i}"
        })
        if response.status_code == 201:
            user_tokens.append(response.json()["token"])
    
    # Like concurrently
    def like_post(token):
        return requests.post(f"{BASE_URL}/posts/like",
            json={"post_id": concurrent_post_id, "liked": True},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            })
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(like_post, token) for token in user_tokens]
        concurrent.futures.wait(futures)
    
    # Verify like count
    response = requests.get(f"{BASE_URL}/posts/details?post_id={concurrent_post_id}",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    data = response.json()
    if data["like_count"] == len(user_tokens):
        results.pass_test("Concurrency - Likes")
    else:
        results.fail_test("Concurrency - Likes", f"Expected {len(user_tokens)} likes, got {data['like_count']}")
except Exception as e:
    results.fail_test("Concurrency - Likes", str(e))

# Test 32: Edge Case - Empty Posts List
try:
    response = requests.post(f"{BASE_URL}/auth/register", json={
        "username": "emptyuser",
        "password": "pass",
        "display_name": "Empty"
    })
    empty_token = response.json()["token"]
    empty_id = response.json()["user_id"]
    
    response = requests.get(f"{BASE_URL}/user/get_posts?user_id={empty_id}",
        headers={"Authorization": f"Bearer {empty_token}"})
    
    if assert_status(response, 200, "Edge Case - Empty Posts"):
        data = assert_json(response, "Edge Case - Empty Posts")
        if data and data["posts"] == [] and data["next_cursor"] is None:
            results.pass_test("Edge Case - Empty Posts")
except Exception as e:
    results.fail_test("Edge Case - Empty Posts", str(e))

# Test 33: Edge Case - comment_count Only Direct Children
try:
    # Create parent post
    response = requests.post(f"{BASE_URL}/posts/create",
        files={"content": (None, "Parent post")},
        headers={"Authorization": f"Bearer {alice_token}"})
    parent_id = response.json()["post_id"]
    
    # Create direct child
    response = requests.post(f"{BASE_URL}/posts/create",
        files={
            "content": (None, "Child comment"),
            "parent_post_id": (None, parent_id)
        },
        headers={"Authorization": f"Bearer {bob_token}"})
    child_id = response.json()["post_id"]
    
    # Create grandchild (child of child)
    response = requests.post(f"{BASE_URL}/posts/create",
        files={
            "content": (None, "Grandchild comment"),
            "parent_post_id": (None, child_id)
        },
        headers={"Authorization": f"Bearer {bob_token}"})
    
    # Check parent comment_count (should be 1, not 2)
    response = requests.get(f"{BASE_URL}/posts/details?post_id={parent_id}",
        headers={"Authorization": f"Bearer {alice_token}"})
    
    data = response.json()
    if data["comment_count"] == 1:
        results.pass_test("Edge Case - comment_count Direct Children Only")
    else:
        results.fail_test("Edge Case - comment_count Direct Children Only", 
            f"Expected comment_count=1, got {data['comment_count']}")
except Exception as e:
    results.fail_test("Edge Case - comment_count Direct Children Only", str(e))

# Summary
success = results.summary()
sys.exit(0 if success else 1)