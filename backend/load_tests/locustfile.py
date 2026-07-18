"""
Locust load test for SentinelRAG.

Usage:
    locust -f load_tests/locustfile.py --host=http://localhost:8000
    locust -f load_tests/locustfile.py --host=http://localhost:8000 --headless -u 10 -r 2 --run-time 60s
"""

import random
import uuid
from locust import HttpUser, task, between

BENCHMARK_QUESTIONS = [
    "What was the total revenue in Q4 2024?",
    "How does the revenue compare to the previous quarter?",
    "What were the operating expenses for the fiscal year?",
    "What is the cash flow from operations?",
    "What was the growth rate year over year?",
    "What are the total assets reported?",
    "What is the net income margin?",
    "What was the earnings per share?",
    "What is the debt to equity ratio?",
    "How many employees does the company have?",
    "What is the research and development spending?",
    "What were the capital expenditures?",
    "What is the return on equity?",
    "What is the current ratio?",
    "What was the free cash flow?",
    "What is the dividend yield?",
    "What were the share buybacks?",
    "What is the market capitalization?",
]


class SentinelRAGUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.session_id = str(uuid.uuid4())
        self.headers = {"X-Request-ID": self.session_id, "Content-Type": "application/json"}

    @task(3)
    def health_check(self):
        self.client.get("/api/v1/health", headers=self.headers, name="GET /health")

    @task(2)
    def readiness_check(self):
        self.client.get("/api/v1/ready", headers=self.headers, name="GET /ready")

    @task(5)
    def chat_query(self):
        question = random.choice(BENCHMARK_QUESTIONS)
        payload = {"question": question}
        with self.client.post(
            "/api/v1/chat",
            json=payload,
            headers=self.headers,
            name="POST /chat",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("confidence", 0) < 0:
                    response.failure(f"Negative confidence: {data.get('confidence')}")
                if data.get("confidence_level") not in ("HIGH", "MEDIUM", "LOW"):
                    response.failure(f"Invalid confidence level: {data.get('confidence_level')}")
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(2)
    def search_query(self):
        question = random.choice(BENCHMARK_QUESTIONS)
        payload = {"query": question}
        with self.client.post(
            "/api/v1/search",
            json=payload,
            headers=self.headers,
            name="POST /search",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "results" not in data:
                    response.failure("Missing results field")
                if "latencies" not in data:
                    response.failure("Missing latencies field")
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Unexpected status: {response.status_code}")

    @task(1)
    def performance_metrics(self):
        endpoints = [
            "/api/v1/metrics/performance",
            "/api/v1/metrics/system",
            "/api/v1/metrics/errors",
        ]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, headers=self.headers, name=f"GET {endpoint}")

    @task(1)
    def evaluation_report(self):
        self.client.get("/api/v1/evaluation/report", headers=self.headers, name="GET /evaluation/report")

    @task(1)
    def evaluation_history(self):
        self.client.get("/api/v1/evaluation/history", headers=self.headers, name="GET /evaluation/history")

    @task(1)
    def document_list(self):
        self.client.get("/api/v1/document/nonexistent/chunks", headers=self.headers, name="GET /document/{id}/chunks")

    @task(1)
    def chat_empty_question(self):
        payload = {"question": ""}
        self.client.post(
            "/api/v1/chat",
            json=payload,
            headers=self.headers,
            name="POST /chat (empty)",
        )

    @task(1)
    def chat_long_question(self):
        payload = {"question": "What " + "very " * 100 + "is the revenue?"}
        self.client.post(
            "/api/v1/chat",
            json=payload,
            headers=self.headers,
            name="POST /chat (long)",
        )


class SentinelRAGHealthCheck(HttpUser):
    wait_time = between(0.5, 1)
    weight = 3

    @task
    def health(self):
        self.client.get("/api/v1/health", name="GET /health (lightweight)")
