import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "datasets" / "benchmark.json"


def load_dataset(path: str | Path | None = None) -> list[dict[str, Any]]:
    path = Path(path) if path else DEFAULT_DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Dataset must be a JSON array")
    return data


def get_dataset_summary(data: list[dict[str, Any]]) -> dict[str, Any]:
    categories: dict[str, int] = {}
    for item in data:
        cat = item.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "total": len(data),
        "categories": categories,
        "has_contradiction": sum(1 for d in data if d.get("has_contradiction", False)),
        "needs_clarification": sum(1 for d in data if d.get("needs_clarification", False)),
        "missing_context": sum(1 for d in data if not d.get("has_context", True)),
    }


def filter_dataset(
    data: list[dict[str, Any]],
    categories: list[str] | None = None,
    tags: list[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    filtered = data

    if categories:
        filtered = [d for d in filtered if d.get("category") in categories]

    if tags:
        filtered = [
            d for d in filtered
            if any(t in d.get("tags", []) for t in tags)
        ]

    if limit and limit < len(filtered):
        filtered = filtered[:limit]

    return filtered
