"""Run the SentinelRAG benchmark against a deployment and write a Markdown report.

    python scripts/run_benchmark.py --base-url https://your-app.up.railway.app

It signs up (or logs in) a throwaway benchmark user, uploads and embeds the corpus in
backend/evaluation/corpus/, triggers POST /api/v1/evaluate (baseline RAG vs the self-correcting
pipeline over the 18 questions in backend/evaluation/datasets/benchmark.json), waits for it, and
saves BENCHMARK.md. Needs `httpx` (already a backend dependency).
"""
import argparse
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = ROOT / "backend" / "evaluation" / "corpus"

METRICS = [
    ("avg_faithfulness", "Faithfulness", "higher"),
    ("avg_hallucination", "Hallucination rate", "lower"),
    ("avg_answer_relevancy", "Answer relevancy", "higher"),
    ("avg_context_precision", "Context precision", "higher"),
    ("avg_context_recall", "Context recall", "higher"),
    ("avg_correctness", "Correctness", "higher"),
    ("avg_unsupported_answer_rate", "Unsupported-answer rate", "lower"),
]


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def authenticate(client: httpx.Client, email: str, password: str) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        response = client.post("/api/v1/auth/register", json={"name": "Benchmark", "email": email, "password": password})
    response.raise_for_status()
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"


def upload_corpus(client: httpx.Client) -> None:
    existing = {d["filename"]: d for d in client.get("/api/v1/documents").json()}
    for pdf in sorted(CORPUS_DIR.glob("*.pdf")):
        doc = existing.get(pdf.name)
        if doc is None:
            log(f"uploading {pdf.name}")
            response = client.post("/api/v1/ingest", files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")})
            response.raise_for_status()
            doc_id = response.json()["document_id"]
        else:
            doc_id = doc["id"]
        if doc is None or doc["status"] != "embedded":
            log(f"embedding {pdf.name}")
            client.post(f"/api/v1/embed/{doc_id}").raise_for_status()


def run_evaluation(client: httpx.Client, timeout_s: int) -> dict:
    started = client.post("/api/v1/evaluate")
    started.raise_for_status()
    eval_id = started.json()["evaluation_id"]
    log(f"evaluation {eval_id} started ({started.json()['total_questions']} questions)")

    deadline = time.time() + timeout_s
    last = None
    polls = 0
    while time.time() < deadline:
        polls += 1
        response = client.get(f"/api/v1/evaluation/status/{eval_id}")
        status = response.json() if response.status_code == 200 else {}
        progress = f"{status.get('progress', 0)}/{status.get('total', '?')}"
        if (status.get("status"), progress) != last:
            log(f"status {status.get('status', f'http {response.status_code}')} {progress}")
            last = (status.get("status"), progress)
        if status.get("status") == "failed":
            raise SystemExit(f"evaluation failed: {status.get('error')}")
        # The status file is advisory; the saved report for this run id is the real signal that it is done.
        if status.get("status") == "completed" or polls % 3 == 0:
            report = client.get("/api/v1/evaluation/report")
            if report.status_code == 200 and report.json().get("evaluation_id") == eval_id:
                return report.json()
        time.sleep(10)
    raise SystemExit("timed out waiting for the evaluation")


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


sys.path.insert(0, str(ROOT / "backend"))
from evaluation.behaviour import behaviour_checks  # noqa: E402


def render(report: dict, base_url: str, model: str) -> str:
    summary = report["summary"]
    base, sent = summary["baseline"], summary["sentinel"]
    lines = [
        "# SentinelRAG benchmark results",
        "",
        f"- Run: `{report['evaluation_id']}` on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Deployment: {base_url}  |  LLM: `{model}`",
        f"- Questions: {report['total_questions']} over the 6-document corpus in `backend/evaluation/corpus/`",
        "",
        "Baseline = one hybrid retrieval + one answer. SentinelRAG = the full self-correcting pipeline.",
        "",
        "## Behaviour checks",
        "",
        "What each kind of question should produce. Unlike the keyword metrics below, these are not noisy.",
        "",
        "| Check | Baseline | SentinelRAG |",
        "|---|---|---|",
        *[f"| {c['label']} | {c['baseline']}/{c['total']} | {c['sentinel']}/{c['total']} |" for c in behaviour_checks(report)],
        "",
        "## Keyword metrics",
        "",
        "Keyword-overlap heuristics over 18 questions: run-to-run swings of several points are normal here (a raw-text fallback answer, which echoes the context, scores well on faithfulness), so do not read small gaps as wins or losses.",
        "",
        "| Metric | Baseline | SentinelRAG | Better |",
        "|---|---|---|---|",
    ]
    for key, label, direction in METRICS:
        b, s = base.get(key, {}).get("value"), sent.get(key, {}).get("value")
        if b is None or s is None:
            continue
        better = "tie" if abs(s - b) < 1e-9 else ("SentinelRAG" if (s > b) == (direction == "higher") else "Baseline")
        lines.append(f"| {label} | {pct(b)} | {pct(s)} | {better} |")
    bl, sl = base.get("latency", {}).get("value"), sent.get("latency", {}).get("value")
    if bl is not None and sl is not None:
        lines.append(f"| Mean latency | {bl / 1000:.1f}s | {sl / 1000:.1f}s | {'Baseline' if bl < sl else 'SentinelRAG'} |")

    def fell_back(pipeline: str) -> list[str]:
        marker = "Based on the retrieved documents (source:"
        return [pq["id"] for pq in report["per_question"] if (pq[pipeline].get("answer") or "").startswith(marker)]

    base_fb, sent_fb = fell_back("baseline"), fell_back("sentinel")
    lines += [
        "",
        f"Answers that fell back to raw retrieved text because the LLM call failed (usually the provider's rate limit):"
        f" baseline {len(base_fb)}/{report['total_questions']}, SentinelRAG {len(sent_fb)}/{report['total_questions']}"
        f"{' (questions ' + ', '.join(sent_fb) + ')' if sent_fb else ''}. These count against the pipeline that hit them.",
    ]
    sentinel_rows = [pq["sentinel"] for pq in report["per_question"]]
    clarified = [pq["id"] for pq in report["per_question"] if pq["sentinel"].get("clarification_needed")]
    unanswered = [
        pq["id"] for pq in report["per_question"]
        if pq["sentinel"].get("answer") is None and not pq["sentinel"].get("clarification_needed")
    ]
    lines.append(
        f"SentinelRAG asked a clarifying question instead of answering for {len(clarified)}/{report['total_questions']}"
        f"{' (questions ' + ', '.join(clarified) + ')' if clarified else ''}; it returned nothing at all for "
        f"{len(unanswered)}/{len(sentinel_rows)}."
    )

    lines += ["", "## Behaviour by category", "", "| Category | Questions | Retried | Contradiction flagged | Clarification asked | Refused (no evidence) |", "|---|---|---|---|---|---|"]
    by_cat: dict[str, list[dict]] = {}
    for pq in report["per_question"]:
        by_cat.setdefault(pq["category"], []).append(pq)
    for cat, rows in by_cat.items():
        retried = sum(1 for r in rows if r["sentinel"].get("retry_count", 0) > 0)
        contra = sum(1 for r in rows if r["sentinel"].get("contradiction_detected"))
        clar = sum(1 for r in rows if r["sentinel"].get("clarification_needed"))
        refused = sum(1 for r in rows if "enough" in (r["sentinel"].get("answer") or "").lower() or "no relevant" in (r["sentinel"].get("answer") or "").lower())
        lines.append(f"| {cat} | {len(rows)} | {retried} | {contra} | {clar} | {refused} |")

    lines += ["", "## Per question", ""]
    for pq in report["per_question"]:
        lines += [
            f"**{pq['id']}. {pq['question']}** ({pq['category']})",
            f"- Expected: {pq['ground_truth'][:200]}",
            f"- Baseline: {(pq['baseline']['answer'] or '')[:200].replace(chr(10), ' ')}",
            f"- SentinelRAG: {(pq['sentinel']['answer'] or '')[:200].replace(chr(10), ' ')}"
            f"  _(path: {' > '.join(pq['sentinel'].get('reasoning_path', []))})_",
            "",
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--email", default=None, help="benchmark user (default: a stable throwaway address)")
    parser.add_argument("--password", default=None)
    parser.add_argument("--output", default=str(ROOT / "BENCHMARK.md"))
    parser.add_argument("--timeout", type=int, default=2400, help="seconds to wait for the evaluation")
    args = parser.parse_args()

    email = args.email or "benchmark@example.invalid"
    password = args.password or "Benchmark-" + uuid.uuid5(uuid.NAMESPACE_DNS, args.base_url).hex[:16]

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=300) as client:
        log("checking the deployment")
        ready = client.get("/api/v1/ready").json()
        if not ready.get("ready") or ready["llm"]["status"] != "configured":
            sys.exit(f"deployment is not ready for a benchmark: {ready}")
        authenticate(client, email, password)
        upload_corpus(client)
        report = run_evaluation(client, args.timeout)
        Path(args.output).write_text(render(report, args.base_url, ready["llm"].get("model", "?")), encoding="utf-8")
        log(f"wrote {args.output}")


if __name__ == "__main__":
    main()
