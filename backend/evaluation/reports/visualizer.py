import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available, visualizations will be skipped")


REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


class Visualizer:
    def __init__(self, output_dir: str | Path | None = None) -> None:
        self.output_dir = Path(output_dir) if output_dir else REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_all(
        self,
        baseline_metrics: dict[str, Any],
        sentinel_metrics: dict[str, Any],
        comparison: dict[str, Any],
    ) -> list[str]:
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("Skipping visualizations: matplotlib not installed")
            return []

        generated = []

        hallucination_chart = self._plot_comparison_bar(
            "Hallucination Rate Comparison",
            "Hallucination Rate (%)",
            {"Baseline": baseline_metrics.get("avg_hallucination", {}).get("value", 0) * 100,
             "SentinelRAG": sentinel_metrics.get("avg_hallucination", {}).get("value", 0) * 100},
            "hallucination_comparison.png",
            color_map={"Baseline": "#e74c3c", "SentinelRAG": "#2ecc71"},
        )
        if hallucination_chart:
            generated.append(hallucination_chart)

        faithfulness_chart = self._plot_comparison_bar(
            "Faithfulness Comparison",
            "Faithfulness Score",
            {"Baseline": baseline_metrics.get("avg_faithfulness", {}).get("value", 0),
             "SentinelRAG": sentinel_metrics.get("avg_faithfulness", {}).get("value", 0)},
            "faithfulness_comparison.png",
            color_map={"Baseline": "#3498db", "SentinelRAG": "#2ecc71"},
        )
        if faithfulness_chart:
            generated.append(faithfulness_chart)

        latency_chart = self._plot_comparison_bar(
            "Latency Comparison",
            "Average Latency (ms)",
            {"Baseline": baseline_metrics.get("latency", {}).get("details", {}).get("average_ms", 0),
             "SentinelRAG": sentinel_metrics.get("latency", {}).get("details", {}).get("average_ms", 0)},
            "latency_comparison.png",
            color_map={"Baseline": "#f39c12", "SentinelRAG": "#9b59b6"},
        )
        if latency_chart:
            generated.append(latency_chart)

        overall_chart = self._plot_overall_comparison(
            baseline_metrics,
            sentinel_metrics,
            "overall_comparison.png",
        )
        if overall_chart:
            generated.append(overall_chart)

        radar_chart = self._plot_radar_comparison(
            baseline_metrics,
            sentinel_metrics,
            "radar_comparison.png",
        )
        if radar_chart:
            generated.append(radar_chart)

        logger.info("Generated %d visualization charts", len(generated))
        return generated

    def _plot_comparison_bar(
        self,
        title: str,
        ylabel: str,
        data: dict[str, float],
        filename: str,
        color_map: dict[str, str] | None = None,
    ) -> str | None:
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            fig, ax = plt.subplots(figsize=(8, 5))
            labels = list(data.keys())
            values = list(data.values())
            colors = [color_map.get(l, "#3498db") for l in labels] if color_map else ["#3498db", "#2ecc71"]

            bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="white", linewidth=1.5)

            for bar, val in zip(bars, values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.02,
                    f"{val:.2f}",
                    ha="center", va="bottom", fontweight="bold", fontsize=11,
                )

            ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
            ax.set_ylabel(ylabel, fontsize=11)
            ax.set_ylim(0, max(values) * 1.25 if values else 1.0)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(axis="x", labelsize=11)

            filepath = self.output_dir / filename
            plt.tight_layout()
            plt.savefig(filepath, dpi=150, bbox_inches="tight")
            plt.close(fig)
            logger.info("Saved chart: %s", filepath)
            return str(filepath)
        except Exception as e:
            logger.warning("Failed to generate chart '%s': %s", title, e)
            return None

    def _plot_overall_comparison(
        self,
        baseline_metrics: dict[str, Any],
        sentinel_metrics: dict[str, Any],
        filename: str,
    ) -> str | None:
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            metric_names = [
                ("avg_faithfulness", "Faithfulness"),
                ("avg_answer_relevancy", "Relevancy"),
                ("avg_context_precision", "Precision"),
                ("avg_context_recall", "Recall"),
                ("avg_correctness", "Correctness"),
                ("avg_hallucination", "Hallucination"),
            ]

            labels = [m[1] for m in metric_names]
            b_vals = [baseline_metrics.get(m[0], {}).get("value", 0) for m in metric_names]
            s_vals = [sentinel_metrics.get(m[0], {}).get("value", 0) for m in metric_names]

            x = np.arange(len(labels))
            width = 0.35

            fig, ax = plt.subplots(figsize=(12, 6))
            bars1 = ax.bar(x - width / 2, b_vals, width, label="Baseline", color="#3498db", edgecolor="white")
            bars2 = ax.bar(x + width / 2, s_vals, width, label="SentinelRAG", color="#2ecc71", edgecolor="white")

            ax.set_title("Overall Performance Comparison", fontsize=14, fontweight="bold", pad=15)
            ax.set_xticks(x)
            ax.set_xticklabels(labels, fontsize=10)
            ax.legend(fontsize=11)
            ax.set_ylabel("Score", fontsize=11)
            ax.set_ylim(0, 1.2)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            for bar in bars1:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, h, f"{h:.2f}", ha="center", va="bottom", fontsize=8)
            for bar in bars2:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, h, f"{h:.2f}", ha="center", va="bottom", fontsize=8)

            filepath = self.output_dir / filename
            plt.tight_layout()
            plt.savefig(filepath, dpi=150, bbox_inches="tight")
            plt.close(fig)
            logger.info("Saved overall chart: %s", filepath)
            return str(filepath)
        except Exception as e:
            logger.warning("Failed to generate overall chart: %s", e)
            return None

    def _plot_radar_comparison(
        self,
        baseline_metrics: dict[str, Any],
        sentinel_metrics: dict[str, Any],
        filename: str,
    ) -> str | None:
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            metric_names = [
                ("avg_faithfulness", "Faithfulness"),
                ("avg_answer_relevancy", "Relevancy"),
                ("avg_context_precision", "Precision"),
                ("avg_context_recall", "Recall"),
                ("avg_correctness", "Correctness"),
            ]

            labels = [m[1] for m in metric_names]
            b_vals = [baseline_metrics.get(m[0], {}).get("value", 0) for m in metric_names]
            s_vals = [sentinel_metrics.get(m[0], {}).get("value", 0) for m in metric_names]

            num_vars = len(labels)
            angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
            angles += angles[:1]

            b_vals_closed = b_vals + b_vals[:1]
            s_vals_closed = s_vals + s_vals[:1]

            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
            ax.plot(angles, b_vals_closed, "o-", linewidth=2, label="Baseline", color="#3498db")
            ax.fill(angles, b_vals_closed, alpha=0.1, color="#3498db")
            ax.plot(angles, s_vals_closed, "o-", linewidth=2, label="SentinelRAG", color="#2ecc71")
            ax.fill(angles, s_vals_closed, alpha=0.1, color="#2ecc71")

            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels, fontsize=10)
            ax.set_ylim(0, 1.0)
            ax.set_title("SentinelRAG vs Baseline — Radar", fontsize=14, fontweight="bold", pad=20)
            ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=11)

            filepath = self.output_dir / filename
            plt.tight_layout()
            plt.savefig(filepath, dpi=150, bbox_inches="tight")

            plt.close(fig)
            logger.info("Saved radar chart: %s", filepath)
            return str(filepath)
        except Exception as e:
            logger.warning("Failed to generate radar chart: %s", e)
            return None
