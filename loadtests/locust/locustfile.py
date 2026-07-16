"""
Locust load profiles for RAGInspector.

Users:
  - HealthUser: /live, /health, /api/v1/ops/ready
  - AuthShapeUser: login attempt shape (expects success or 401)
  - MetricsUser: dashboard metrics with Bearer token (optional)

Stage comments (use with --users / --spawn-rate or Locust UI Load Shape):
  - Stage 10 VU:   --users 10  --spawn-rate 2
  - Stage 100 VU:  --users 100 --spawn-rate 10
  - Stage 500 VU:  --users 500 --spawn-rate 25
  - Stage 1000 VU: --users 1000 --spawn-rate 50

Usage:
  locust -f loadtests/locust/locustfile.py --host http://localhost:8000
  locust -f loadtests/locust/locustfile.py --host http://localhost:8000 \\
    --users 100 --spawn-rate 10 --run-time 3m --headless
"""

from __future__ import annotations

import os

from locust import HttpUser, between, task


BASE_HOST = os.getenv("BASE_URL", "http://localhost:8000")
DEMO_EMAIL = os.getenv("DEMO_EMAIL", "demo@example.com")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "DemoPass123!")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "")


class HealthUser(HttpUser):
    """Cheap probe traffic matching k6 health scenarios."""

    weight = 5
    wait_time = between(0.2, 0.8)

    @task(3)
    def live(self) -> None:
        with self.client.get("/live", name="GET /live", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"unexpected status {resp.status_code}")

    @task(2)
    def health(self) -> None:
        self.client.get("/health", name="GET /health")

    @task(2)
    def ready(self) -> None:
        with self.client.get(
            "/api/v1/ops/ready", name="GET /api/v1/ops/ready", catch_response=True
        ) as resp:
            if resp.status_code in (200, 503):
                resp.success()
            else:
                resp.failure(f"unexpected status {resp.status_code}")


class AuthShapeUser(HttpUser):
    """
    Login attempt shape: posts credentials at a low rate.
    Successful demos return 200; missing seed users return 401 — both count as
    shaping auth path load, not as application errors for this profile.
    """

    weight = 1
    wait_time = between(1.0, 3.0)

    @task
    def login_attempt(self) -> None:
        with self.client.post(
            "/api/v1/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            name="POST /api/v1/auth/login",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 401, 403, 422):
                resp.success()
            elif resp.status_code == 429:
                resp.success()  # rate limit is expected under stress
            else:
                resp.failure(f"unexpected status {resp.status_code}")


class MetricsUser(HttpUser):
    """Authenticated metrics reads when ACCESS_TOKEN is provided."""

    weight = 2
    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        self.token = ACCESS_TOKEN
        if not self.token:
            # Best-effort login so headless runs still exercise metrics when demo exists.
            resp = self.client.post(
                "/api/v1/auth/login",
                json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                name="POST /api/v1/auth/login (bootstrap)",
            )
            if resp.status_code == 200:
                data = resp.json()
                self.token = data.get("access_token") or ""

    @task(3)
    def dashboard(self) -> None:
        if not self.token:
            return
        self.client.get(
            "/api/v1/metrics/dashboard",
            headers={"Authorization": f"Bearer {self.token}"},
            name="GET /api/v1/metrics/dashboard",
        )

    @task(1)
    def timeseries(self) -> None:
        if not self.token:
            return
        self.client.get(
            "/api/v1/metrics/timeseries?days=7",
            headers={"Authorization": f"Bearer {self.token}"},
            name="GET /api/v1/metrics/timeseries",
        )
