import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


class ReportGenerator:
    def __init__(self, output_dir: str | Path | None = None) -> None:
        self.output_dir = Path(output_dir) if output_dir else REPORTS_DIR
        self.results_dir = RESULTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(self, result: dict[str, Any]) -> dict[str, str]:
        files = {}

        json_path = self._generate_json(result)
        if json_path:
            files["json"] = json_path

        csv_path = self._generate_csv(result)
        if csv_path:
            files["csv"] = csv_path

        md_path = self._generate_markdown(result)
        if md_path:
            files["markdown"] = md_path

        logger.info("Generated report files: %s", files)
        return files

    def _generate_json(self, result: dict[str, Any]) -> str | None:
        try:
            path = self.output_dir / "evaluation_results.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
            logger.info("JSON report saved: %s", path)
            return str(path)
        except Exception as e:
            logger.error("Failed to generate JSON report: %s", e)
            return None

    def _generate_csv(self, result: dict[str, Any]) -> str | None:
        try:
            path = self.output_dir / "evaluation_results.csv"
            per_question = result.get("per_question", [])

            if not per_question:
                logger.warning("No per-question data for CSV report")
                return None

            fieldnames = [
                "id", "question", "category", "ground_truth",
                "baseline_answer", "baseline_confidence", "baseline_confidence_level",
                "sentinel_answer", "sentinel_confidence", "sentinel_confidence_level",
                "sentinel_contradiction_detected", "sentinel_clarification_needed",
                "sentinel_reasoning_path",
            ]

            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for pq in per_question:
                    writer.writerow({
                        "id": pq["id"],
                        "question": pq["question"],
                        "category": pq["category"],
                        "ground_truth": pq["ground_truth"],
                        "baseline_answer": pq["baseline"]["answer"],
                        "baseline_confidence": pq["baseline"]["confidence_score"],
                        "baseline_confidence_level": pq["baseline"]["confidence_level"],
                        "sentinel_answer": pq["sentinel"]["answer"],
                        "sentinel_confidence": pq["sentinel"]["confidence_score"],
                        "sentinel_confidence_level": pq["sentinel"]["confidence_level"],
                        "sentinel_contradiction_detected": pq["sentinel"]["contradiction_detected"],
                        "sentinel_clarification_needed": pq["sentinel"]["clarification_needed"],
                        "sentinel_reasoning_path": " -> ".join(pq["sentinel"]["reasoning_path"]),
                    })

            logger.info("CSV report saved: %s", path)
            return str(path)
        except Exception as e:
            logger.error("Failed to generate CSV report: %s", e)
            return None

    def _generate_markdown(self, result: dict[str, Any]) -> str | None:
        try:
            path = self.output_dir / "evaluation_report.md"
            summary = result.get("summary", {})
            comparison = summary.get("comparison", {})
            baseline = summary.get("baseline", {})
            sentinel = summary.get("sentinel", {})
            per_question = result.get("per_question", [])

            lines: list[str] = []
            lines.append("# SentinelRAG Evaluation Report")
            lines.append("")
            lines.append(f"- **Evaluation ID:** `{result.get('evaluation_id', 'unknown')}`")
            lines.append(f"- **Timestamp:** {result.get('timestamp', 'unknown')}")
            lines.append(f"- **Dataset:** {result.get('dataset', 'unknown')}")
            lines.append(f"- **Total Questions:** {result.get('total_questions', 0)}")
            lines.append("")
            lines.append("---")
            lines.append("")

            lines.append("## Overall Summary")
            lines.append("")
            lines.append("| Metric | Baseline | SentinelRAG | Change | Improvement |")
            lines.append("|--------|----------|-------------|--------|-------------|")

            metric_display = {
                "avg_faithfulness": "Faithfulness",
                "avg_answer_relevancy": "Answer Relevancy",
                "avg_context_precision": "Context Precision",
                "avg_context_recall": "Context Recall",
                "avg_hallucination": "Hallucination Rate",
                "avg_bias": "Bias Score",
                "avg_toxicity": "Toxicity Score",
                "avg_correctness": "Correctness",
                "avg_unsupported_answer_rate": "Unsupported Answer Rate",
                "latency": "Avg Latency (ms)",
            }

            for key, display_name in metric_display.items():
                if key in comparison:
                    c = comparison[key]
                    arrow = "↑" if c.get("improved") else "↓"
                    change_str = f"{c.get('relative_change_pct', 0):+.1f}%"
                    lines.append(
                        f"| {display_name} | {c['baseline']:.4f} | {c['sentinel']:.4f} | "
                        f"{change_str} | {arrow} |"
                    )

            lines.append("")
            lines.append("---")
            lines.append("")

            lines.append("## Custom Metrics")
            lines.append("")

            custom_metrics = [
                ("confidence_calibration", "Confidence Calibration"),
                ("citation_accuracy", "Citation Accuracy"),
                ("contradiction_detection_rate", "Contradiction Detection Rate"),
                ("retry_success_rate", "Retry Success Rate"),
                ("clarification_rate", "Clarification Rate"),
            ]

            for key, display_name in custom_metrics:
                for source_name, source_label in [("baseline", "Baseline"), ("sentinel", "SentinelRAG")]:
                    source = summary.get(source_name, {})
                    if key in source:
                        val = source[key].get("value", "N/A")
                        if isinstance(val, float):
                            lines.append(f"- **{source_label} {display_name}:** {val:.4f}")
                        else:
                            lines.append(f"- **{source_label} {display_name}:** {val}")

            lines.append("")
            lines.append("---")
            lines.append("")

            lines.append("## Per-Question Breakdown")
            lines.append("")
            lines.append("| ID | Category | Question | Baseline Conf | Sentinel Conf | Path |")
            lines.append("|----|----------|----------|--------------|---------------|------|")

            for pq in per_question:
                qid = pq["id"]
                cat = pq["category"]
                qtext = pq["question"][:50] + "..." if len(pq["question"]) > 50 else pq["question"]
                b_conf = f"{pq['baseline']['confidence_score']:.1f}"
                s_conf = f"{pq['sentinel']['confidence_score']:.1f}"
                reasoning_path_str = " -> ".join(pq["sentinel"]["reasoning_path"][-3:])
                lines.append(f"| {qid} | {cat} | {qtext} | {b_conf} | {s_conf} | {reasoning_path_str} |")

            lines.append("")
            lines.append("---")
            lines.append("")

            lines.append("## Failure Modes")
            lines.append("")
            failure_modes = result.get("failure_modes", {})
            lines.append("| Failure Mode | Count |")
            lines.append("|--------------|-------|")
            for mode, count in failure_modes.items():
                lines.append(f"| {mode.replace('_', ' ').title()} | {count} |")

            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

            content = "\n".join(lines)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info("Markdown report saved: %s", path)
            return str(path)
        except Exception as e:
            logger.error("Failed to generate Markdown report: %s", e)
            return None

    def load_latest_result(self) -> dict[str, Any] | None:
        path = self.results_dir / "evaluation_results.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def load_history(self) -> list[dict[str, Any]]:
        path = self.results_dir / "evaluation_history.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []
