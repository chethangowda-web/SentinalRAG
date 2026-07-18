"""
Standalone performance benchmark runner.

Usage:
    python -m performance.benchmark_runner
    python -m performance.benchmark_runner --output ./reports --samples 100
"""

import argparse
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("benchmark")


@dataclass
class BenchmarkResult:
    operation: str
    samples: list[float] = field(default_factory=list)
    errors: int = 0

    @property
    def avg_ms(self) -> float:
        return sum(self.samples) / len(self.samples) if self.samples else 0

    @property
    def min_ms(self) -> float:
        return min(self.samples) if self.samples else 0

    @property
    def max_ms(self) -> float:
        return max(self.samples) if self.samples else 0

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0
        sorted_s = sorted(self.samples)
        idx = int(len(sorted_s) * p / 100)
        return sorted_s[min(idx, len(sorted_s) - 1)]

    @property
    def p50_ms(self) -> float:
        return self.percentile(50)

    @property
    def p95_ms(self) -> float:
        return self.percentile(95)

    @property
    def p99_ms(self) -> float:
        return self.percentile(99)

    @property
    def success_rate(self) -> float:
        total = len(self.samples) + self.errors
        return len(self.samples) / total * 100 if total > 0 else 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "samples": len(self.samples),
            "errors": self.errors,
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
            "success_rate": round(self.success_rate, 2),
        }


class BenchmarkSuite:
    def __init__(self, name: str = "SentinelRAG Performance Benchmark", num_samples: int = 50):
        self.name = name
        self.num_samples = num_samples
        self.results: list[BenchmarkResult] = []
        self.start_time = time.time()

    def benchmark_sync(self, operation: str, fn: Callable, *args, **kwargs) -> BenchmarkResult:
        result = BenchmarkResult(operation=operation)
        logger.info("  Benchmarking %s (%d samples)...", operation, self.num_samples)
        for i in range(self.num_samples):
            try:
                start = time.perf_counter()
                fn(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                result.samples.append(elapsed)
            except Exception as e:
                result.errors += 1
                logger.debug("    Sample %d failed: %s", i + 1, e)
            if (i + 1) % 10 == 0:
                logger.info("    %d/%d samples completed", i + 1, self.num_samples)
        self.results.append(result)
        logger.info("  %s: avg=%.2fms p95=%.2fms p99=%.2fms (rate=%.1f%%)",
                    operation, result.avg_ms, result.p95_ms, result.p99_ms, result.success_rate)
        return result

    async def benchmark_async(self, operation: str, fn: Callable, *args, **kwargs) -> BenchmarkResult:
        result = BenchmarkResult(operation=operation)
        logger.info("  Benchmarking %s (%d samples)...", operation, self.num_samples)
        for i in range(self.num_samples):
            try:
                start = time.perf_counter()
                await fn(*args, **kwargs)
                elapsed = (time.perf_counter() - start) * 1000
                result.samples.append(elapsed)
            except Exception as e:
                result.errors += 1
                logger.debug("    Sample %d failed: %s", i + 1, e)
            if (i + 1) % 10 == 0:
                logger.info("    %d/%d samples completed", i + 1, self.num_samples)
        self.results.append(result)
        logger.info("  %s: avg=%.2fms p95=%.2fms p99=%.2fms (rate=%.1f%%)",
                    operation, result.avg_ms, result.p95_ms, result.p99_ms, result.success_rate)
        return result

    def summary(self) -> dict[str, Any]:
        total_time = time.time() - self.start_time
        all_success = sum(r.success_rate for r in self.results) / len(self.results) if self.results else 0
        return {
            "suite_name": self.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_operations": len(self.results),
            "total_samples": sum(r.samples for r in self.results),
            "duration_seconds": round(total_time, 2),
            "overall_success_rate": round(all_success, 2),
            "results": [r.to_dict() for r in self.results],
        }

    def save(self, output_dir: str = ".") -> Path:
        path = Path(output_dir) / "benchmark_results.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.summary(), f, indent=2)
        logger.info("Benchmark results saved to %s", path)
        return path


def run_benchmarks(num_samples: int = 50) -> BenchmarkSuite:
    logger.info("=" * 60)
    logger.info("SentinelRAG Performance Benchmark")
    logger.info("=" * 60)
    logger.info("Samples per operation: %d", num_samples)
    logger.info("")

    suite = BenchmarkSuite(num_samples=num_samples)

    # Text cleaning
    logger.info("\n[Text Processing]")
    from app.services.text_cleaning import clean_text
    clean_text("warmup")  # Warmup
    suite.benchmark_sync("text_cleaning_small", clean_text, "Small text. " * 100)
    suite.benchmark_sync("text_cleaning_medium", clean_text, "Medium text. " * 1000)
    suite.benchmark_sync("text_cleaning_large", clean_text,
                         "\n".join([f"Page {p}\nContent. " * 50 for p in range(20)]))

    # Chunking
    logger.info("\n[Chunking]")
    from app.services.chunking_service import chunk_text
    chunk_text("warmup")  # Warmup
    suite.benchmark_sync("chunking_small", chunk_text, "word " * 500)
    suite.benchmark_sync("chunking_medium", chunk_text, "word " * 5000)
    suite.benchmark_sync("chunking_large", chunk_text, "\n\n".join([f"Section {i}. " + "word " * 200 for i in range(50)]))

    # Embedding normalization
    logger.info("\n[Embedding]")
    from app.services.embedding_service import normalize_embedding
    normalize_embedding([0.1] * 384)  # Warmup
    vec_small = [0.1 * i for i in range(384)]
    suite.benchmark_sync("embedding_normalize", normalize_embedding, vec_small)

    # Query preprocessing
    logger.info("\n[Query Processing]")
    from app.services.query_preprocessor import preprocess_query
    preprocess_query("warmup")  # Warmup
    suite.benchmark_sync("query_preprocess_short", preprocess_query, "What is the revenue?")
    suite.benchmark_sync("query_preprocess_long", preprocess_query,
                         "What was Apple's total revenue in Q4 2024 and how does it compare to the previous quarter?")

    # Confidence scoring
    logger.info("\n[Confidence Scoring]")
    from app.services.confidence_service import calculate_confidence
    calculate_confidence([{"vector_score": 0.9, "rerank_score": 0.9}])  # Warmup
    scores = [{"vector_score": 0.9 - i * 0.02, "rerank_score": 0.92 - i * 0.02} for i in range(5)]
    suite.benchmark_sync("confidence_scoring", calculate_confidence, scores)

    # Hybrid search fusion
    logger.info("\n[Hybrid Search]")
    from app.services.hybrid_search_service import fuse_results
    v = [{"chunk_id": f"v_{i}", "document_id": "d1", "text": f"text {i}", "score": 0.99 - i * 0.01,
          "page_number": i, "section": "test"} for i in range(20)]
    b = [{"chunk_id": f"b_{i}", "document_id": "d1", "text": f"text {i}", "score": 0.98 - i * 0.01,
          "page_number": i, "section": "test"} for i in range(20)]
    fuse_results(v, b)  # Warmup
    suite.benchmark_sync("rrf_fusion_20x20", fuse_results, v, b)
    v100 = [{"chunk_id": f"v_{i}", "document_id": "d1", "text": f"text {i}", "score": 0.99 - i * 0.001,
             "page_number": i, "section": "test"} for i in range(100)]
    b100 = [{"chunk_id": f"b_{i}", "document_id": "d1", "text": f"text {i}", "score": 0.98 - i * 0.001,
             "page_number": i, "section": "test"} for i in range(100)]
    suite.benchmark_sync("rrf_fusion_100x100", fuse_results, v100, b100)

    # Contradiction detection
    logger.info("\n[Contradiction Detection]")
    from app.services.contradiction_service import detect_contradictions
    detect_contradictions("test", [{"text": "test"}])  # Warmup
    chunks = [
        {"text": "Revenue was $12.4 billion in Q4 2024."},
        {"text": "Revenue was $12.4 billion, representing 15% growth."},
    ]
    suite.benchmark_sync("contradiction_detection", detect_contradictions, "What is revenue?", chunks)

    # Clarification
    logger.info("\n[Clarification]")
    from app.services.clarification_service import detect_ambiguity
    detect_ambiguity("warmup", [{"text": "test"}])  # Warmup
    suite.benchmark_sync("clarification_vague", detect_ambiguity, "What about it?", chunks)
    suite.benchmark_sync("clarification_specific", detect_ambiguity, "What was the revenue in Q4 2024?", chunks)

    logger.info("")
    logger.info("=" * 60)
    logger.info("Benchmark Complete")
    logger.info("Duration: %.1fs", time.time() - suite.start_time)
    logger.info("=" * 60)

    return suite


def main():
    parser = argparse.ArgumentParser(description="SentinelRAG Performance Benchmark")
    parser.add_argument("--samples", type=int, default=50, help="Number of samples per operation")
    parser.add_argument("--output", type=str, default="performance", help="Output directory")
    args = parser.parse_args()

    suite = run_benchmarks(num_samples=args.samples)
    path = suite.save(args.output)

    summary = suite.summary()
    print()
    print(f"{'Operation':<35} {'Avg(ms)':>10} {'P95(ms)':>10} {'P99(ms)':>10} {'Rate(%)':>8}")
    print("-" * 75)
    for r in summary["results"]:
        print(f"{r['operation']:<35} {r['avg_ms']:>10.2f} {r['p95_ms']:>10.2f} {r['p99_ms']:>10.2f} {r['success_rate']:>8.1f}")
    print("-" * 75)
    print(f"Duration: {summary['duration_seconds']:.1f}s | Samples: {summary['total_samples']} | "
          f"Success: {summary['overall_success_rate']:.1f}%")


if __name__ == "__main__":
    main()
