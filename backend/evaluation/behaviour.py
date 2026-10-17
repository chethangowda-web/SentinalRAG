"""What each kind of benchmark question should produce, scored per pipeline.

Unlike the keyword-overlap metrics, these checks are not noisy: a vague question is either answered or
clarified, an unanswerable one is either refused or not. Shared by the evaluation page and
scripts/run_benchmark.py.
"""
from typing import Any

REFUSAL_MARKERS = ("don't have enough", "do not have enough", "no relevant information")
CONFLICT_MARKERS = ("contradict", "conflict", "differ", "depends on", "disagree")
FALLBACK_MARKER = "Based on the retrieved documents (source:"


def _answered(r: dict) -> bool:
    a = r.get("answer") or ""
    return bool(a) and not a.startswith(FALLBACK_MARKER) and not any(m in a.lower() for m in REFUSAL_MARKERS)


def _refused(r: dict) -> bool:
    return any(m in (r.get("answer") or "").lower() for m in REFUSAL_MARKERS)


def _surfaced_conflict(r: dict) -> bool:
    return any(m in (r.get("answer") or "").lower() for m in CONFLICT_MARKERS)


_CHECKS = (
    ("Specific questions answered", "Easy, medium and hard questions get a real answer", ("easy", "medium", "hard"), _answered),
    ("Unanswerable questions refused", "Questions the documents cannot answer are declined, not invented", ("missing_context",), _refused),
    ("Conflicting sources surfaced", "When two documents disagree, the answer says so", ("contradictory",), _surfaced_conflict),
    ("Vague questions clarified", "Ambiguous questions get a clarifying question", ("ambiguous",), lambda r: bool(r.get("clarification_needed"))),
)


def behaviour_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Passed/total per pipeline for each behaviour the benchmark's question categories test."""
    out = []
    for label, description, categories, ok in _CHECKS:
        rows = [pq for pq in report.get("per_question", []) if pq.get("category") in categories]
        out.append({
            "label": label,
            "description": description,
            "total": len(rows),
            "baseline": sum(1 for pq in rows if ok(pq["baseline"])),
            "sentinel": sum(1 for pq in rows if ok(pq["sentinel"])),
        })
    return out
