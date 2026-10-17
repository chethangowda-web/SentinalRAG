"""Fire concurrent requests at a deployment and report latency and errors.

    python scripts/load_test.py --base-url https://your-app.up.railway.app --users 20

Searches only (no LLM call), so it spends no model quota. It signs in as a throwaway user and needs at least one
indexed document in that account (the benchmark user from scripts/run_benchmark.py has six).
Note the app rate-limits each user (RATE_LIMIT_MAX_REQUESTS per minute); stay below that or expect 429s.
"""
import argparse
import asyncio
import statistics
import time

import httpx

QUERIES = [
    "What is the refund window?", "uptime guarantee premium", "data retention period for logs",
    "maintenance window schedule", "support languages offered", "service credit if uptime drops",
    "escalation of unresolved tickets", "security incident response time", "annual plan cancellation refund",
    "customer record retention after closure",
]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", default="benchmark@example.invalid")
    parser.add_argument("--password", required=True, help="password of the load-test user")
    parser.add_argument("--users", type=int, default=20, help="simultaneous requests")
    parser.add_argument("--rounds", type=int, default=1, help="how many waves of --users requests")
    args = parser.parse_args()

    async with httpx.AsyncClient(base_url=args.base_url.rstrip("/"), timeout=120) as client:
        login = await client.post("/api/v1/auth/login", json={"email": args.email, "password": args.password})
        login.raise_for_status()
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        async def one(i: int) -> tuple[int | str, float]:
            started = time.perf_counter()
            try:
                # A trailing run of spaces changes nothing for the search but defeats the query cache
                query = QUERIES[i % len(QUERIES)] + " " * (i // len(QUERIES))
                response = await client.post("/api/v1/search", json={"query": query}, headers=headers)
                return response.status_code, time.perf_counter() - started
            except Exception as exc:  # timeouts, resets
                return type(exc).__name__, time.perf_counter() - started

        for wave in range(args.rounds):
            started = time.perf_counter()
            results = await asyncio.gather(*[one(wave * args.users + i) for i in range(args.users)])
            wall = time.perf_counter() - started
            codes: dict[int | str, int] = {}
            for code, _ in results:
                codes[code] = codes.get(code, 0) + 1
            latencies = sorted(seconds for _, seconds in results)
            p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
            print(
                f"wave {wave + 1}: {args.users} requests in {wall:.1f}s ({args.users / wall:.1f}/s) "
                f"codes={codes} p50={statistics.median(latencies):.1f}s p95={p95:.1f}s max={latencies[-1]:.1f}s"
            )


if __name__ == "__main__":
    asyncio.run(main())
