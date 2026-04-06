import os
import random
import time
import uuid
import csv

from locust import HttpUser, between, task, events

ENABLE_AUTH_FLOW = os.getenv("ENABLE_AUTH_FLOW", "false").lower() == "true"


class BackendOptimizerUser(HttpUser):
    wait_time = between(0.05, 0.3)

    def on_start(self):
        self.token = None
        self.created_posts = []

        if ENABLE_AUTH_FLOW:
            self._authenticate()

    def _authenticate(self):
        """Try register first, then login on conflict to get a bearer token."""
        run_id = os.getenv("LOADTEST_RUN_ID", str(int(time.time())))
        nonce = uuid.uuid4().hex[:8]

        username = f"lt_{run_id}_{nonce}"
        password = f"pw_{nonce}"
        display_name = f"Load Tester {nonce}"

        register_payload = {
            "username": username,
            "password": password,
            "display_name": display_name,
        }

        with self.client.post(
            "/auth/register",
            json=register_payload,
            name="POST /auth/register",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                try:
                    data = response.json()
                    token = data.get("token")
                    user_id = data.get("user_id")
                    if token and user_id:
                        self.token = token
                        response.success()
                        return
                    else:
                        response.failure("register succeeded but missing token or user_id")
                        return
                except ValueError:
                    response.failure("register response was not valid JSON")
                    return

            if response.status_code != 409:
                response.failure(f"register failed ({response.status_code})")
                return

        login_payload = {"username": username, "password": password}
        with self.client.post(
            "/auth/login",
            json=login_payload,
            name="POST /auth/login",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    token = data.get("token")
                    if token:
                        self.token = token
                        response.success()
                    else:
                        response.failure("login succeeded but token was missing")
                except ValueError:
                    response.failure("login response was not valid JSON")
            else:
                response.failure(f"login failed ({response.status_code})")

    @task(6)
    def health(self):
        with self.client.get("/health", name="GET /health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"status={response.status_code}")

    @task(4)
    def health_redis(self):
        with self.client.get(
            "/health-redis", name="GET /health-redis", catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"status={response.status_code}")

    @task(2)
    def create_post(self):
        if not ENABLE_AUTH_FLOW or not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {"content": f"load test post {uuid.uuid4().hex[:10]}"}

        files = {
            "media[]": (
                "pixel.txt",
                b"loadtest",
                "text/plain",
            )
        }

        with self.client.post(
            "/posts/create",
            data=payload,
            files=files,
            headers=headers,
            name="POST /posts/create",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                try:
                    data = response.json()
                    post_id = data.get("post_id")
                    if post_id and "author_id" in data and "content" in data:
                        self.created_posts.append(post_id)
                        response.success()
                    else:
                        response.failure("missing required fields (post_id, author_id, content)")
                except ValueError:
                    response.failure("invalid JSON response")
            else:
                response.failure(f"status={response.status_code}")

    @task(3)
    def post_details(self):
        if not ENABLE_AUTH_FLOW or not self.token or not self.created_posts:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        post_id = random.choice(self.created_posts)

        with self.client.get(
            "/posts/details",
            params={"post_id": post_id},
            headers=headers,
            name="GET /posts/details",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "author_id" not in data or "content" not in data:
                        response.failure("missing expected fields in post details")
                        return

                    media_list = data.get("media", [])
                    response.success()

                    # Test media validation
                    for m in media_list:
                        url = m.get("url")
                        if url:
                            with self.client.get(
                                url,
                                headers=headers,
                                name="GET Media",
                                catch_response=True
                            ) as media_response:
                                if media_response.status_code == 200:
                                    media_response.success()
                                else:
                                    media_response.failure(f"status={media_response.status_code}")
                except ValueError:
                    response.failure("invalid JSON response")
            else:
                response.failure(f"status={response.status_code}")

    @task(1)
    def delete_post(self):
        if not ENABLE_AUTH_FLOW or not self.token or not self.created_posts:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        post_id = self.created_posts.pop(0)

        with self.client.post(
            "/posts/delete",
            json={"post_id": post_id},
            headers=headers,
            name="POST /posts/delete",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    if response.json().get("success"):
                        response.success()
                    else:
                        response.failure("success flag not true")
                except ValueError:
                    response.failure("invalid JSON response")
            else:
                response.failure(f"status={response.status_code}")

    @task(3)
    def user_details(self):
        if not ENABLE_AUTH_FLOW or not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        with self.client.get(
            "/user/details",
            headers=headers,
            name="GET /user/details",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "user_id" in data and "username" in data and "post_count" in data:
                        response.success()
                    else:
                        response.failure("missing user_id, username, or post_count")
                except ValueError:
                    response.failure("invalid JSON response")
            else:
                response.failure(f"status={response.status_code}")

    @task(2)
    def user_get_posts(self):
        if not ENABLE_AUTH_FLOW or not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        with self.client.get(
            "/user/get_posts",
            headers=headers,
            name="GET /user/get_posts",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "posts" in data:
                        response.success()
                    else:
                        response.failure("missing posts array")
                except ValueError:
                    response.failure("invalid JSON response")
            else:
                response.failure(f"status={response.status_code}")

    @task(2)
    def user_liked_posts(self):
        if not ENABLE_AUTH_FLOW or not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        with self.client.get(
            "/user/liked_posts",
            headers=headers,
            name="GET /user/liked_posts",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "posts" in data:
                        response.success()
                    else:
                        response.failure("missing posts array")
                except ValueError:
                    response.failure("invalid JSON response")
            else:
                response.failure(f"status={response.status_code}")

    @task(4)
    def post_like(self):
        if not ENABLE_AUTH_FLOW or not self.token or not self.created_posts:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        post_id = random.choice(self.created_posts)
        liked = random.choice([True, False])

        with self.client.post(
            "/posts/like",
            json={"post_id": post_id, "liked": liked},
            headers=headers,
            name="POST /posts/like",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "like_count" in data and "liked_by_me" in data:
                        response.success()
                    else:
                        response.failure("missing like_count or liked_by_me")
                except ValueError:
                    response.failure("invalid JSON response")
            else:
                response.failure(f"status={response.status_code}")

    @task(1)
    def delete_user(self):
        if not ENABLE_AUTH_FLOW or not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}
        with self.client.post(
            "/user/delete",
            json={},
            headers=headers,
            name="POST /user/delete",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    if response.json().get("success"):
                        response.success()
                        self.created_posts = []
                        self._authenticate()
                    else:
                        response.failure("success flag not true")
                except ValueError:
                    response.failure("invalid JSON response")
            else:
                response.failure(f"status={response.status_code}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("Total Requests:", environment.stats.total.num_requests)
    print("Total Failures:", environment.stats.total.num_failures)
    print(f"Success Rate: {round((1 - environment.stats.total.num_failures / max(1, environment.stats.total.num_requests)) * 100, 2)}%")

    if environment.stats.total.num_failures > 0:
        print("\nBreakdown of Failures (HTTP errors or Invalid Data):")
        for key, err in environment.stats.errors.items():
            print(f" - [{err.method}] {err.name}: {err.error} (Occurrences: {err.occurrences})")
    else:
        print("\nAll successful hits retrieved the CORRECT information with NO missing fields!")
    print("="*50 + "\n")

    # Export statistics data to a CSV file automatically
    if not os.path.exists("loadtest"):
        os.makedirs("loadtest")

    csv_file_path = f"loadtest/test_statistics_{int(time.time())}.csv"
    with open(csv_file_path, mode="w", newline="") as f:
        writer = csv.writer(f)
        # Write CSV Headers
        writer.writerow(["Type", "Name", "Requests", "Failures", "Median Response Time", "Average Response Time", "Min Response Time", "Max Response Time"])

        # Write Endpoint Stats
        for endpoint in environment.stats.entries.values():
            writer.writerow([
                endpoint.method,
                endpoint.name,
                endpoint.num_requests,
                endpoint.num_failures,
                endpoint.median_response_time,
                endpoint.avg_response_time,
                endpoint.min_response_time,
                endpoint.max_response_time
            ])

        # Write Totals
        writer.writerow([
            "None", "Aggregated",
            environment.stats.total.num_requests,
            environment.stats.total.num_failures,
            environment.stats.total.median_response_time,
            environment.stats.total.avg_response_time,
            environment.stats.total.min_response_time,
            environment.stats.total.max_response_time
        ])
    print(f"Statistics data downloaded to: {csv_file_path}")
