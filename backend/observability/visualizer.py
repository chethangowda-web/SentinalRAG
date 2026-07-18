import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib not available — chart generation disabled")


class PerformanceVisualizer:
    def __init__(self, output_dir: str = "performance/charts"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.style = "dark_background" if MATPLOTLIB_AVAILABLE else None

    def _setup_style(self):
        if MATPLOTLIB_AVAILABLE and self.style:
            plt.style.use(self.style)

    def _save(self, name: str) -> Path:
        path = self.output_dir / f"{name}.png"
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Saved chart: %s", path)
        return path

    def latency_histogram(self, latencies: dict[str, dict[str, float]]) -> Path:
        if not MATPLOTLIB_AVAILABLE:
            return self._placeholder_chart("latency_histogram")
        self._setup_style()
        fig, ax = plt.subplots(figsize=(10, 6))
        operations = list(latencies.keys())
        avgs = [latencies[op].get("avg", 0) for op in operations]
        p95s = [latencies[op].get("p95", 0) for op in operations]
        short_ops = [op.replace("latency.", "").replace("component.", "")[:20] for op in operations]
        x = range(len(operations))
        width = 0.35
        ax.bar([i - width / 2 for i in x], avgs, width, label="Avg (ms)", color="#22c55e", alpha=0.8)
        ax.bar([i + width / 2 for i in x], p95s, width, label="P95 (ms)", color="#3b82f6", alpha=0.8)
        ax.set_xlabel("Operation")
        ax.set_ylabel("Latency (ms)")
        ax.set_title("Component Latency Distribution")
        ax.set_xticks(list(x))
        ax.set_xticklabels(short_ops, rotation=45, ha="right", fontsize=8)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return self._save("latency_histogram")

    def p95_p99_chart(self, latencies: dict[str, dict[str, float]]) -> Path:
        if not MATPLOTLIB_AVAILABLE:
            return self._placeholder_chart("p95_p99_chart")
        self._setup_style()
        fig, ax = plt.subplots(figsize=(10, 6))
        operations = list(latencies.keys())
        p95s = [latencies[op].get("p95", 0) for op in operations]
        p99s = [latencies[op].get("p99", 0) for op in operations]
        short_ops = [op.replace("latency.", "").replace("component.", "")[:20] for op in operations]
        x = range(len(operations))
        ax.plot(x, p95s, "o-", label="P95 (ms)", color="#3b82f6", linewidth=2, markersize=6)
        ax.plot(x, p99s, "s--", label="P99 (ms)", color="#ef4444", linewidth=2, markersize=6)
        ax.fill_between(x, p95s, p99s, alpha=0.15, color="#ef4444")
        ax.set_xlabel("Operation")
        ax.set_ylabel("Latency (ms)")
        ax.set_title("P95 vs P99 Latency")
        ax.set_xticks(list(x))
        ax.set_xticklabels(short_ops, rotation=45, ha="right", fontsize=8)
        ax.legend()
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return self._save("p95_p99_chart")

    def memory_usage_graph(self, csv_path: Path) -> Path:
        if not MATPLOTLIB_AVAILABLE:
            return self._placeholder_chart("memory_usage")
        self._setup_style()
        import csv
        timestamps, mem_mb, mem_pct = [], [], []
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamps.append(float(row["timestamp"]))
                mem_mb.append(float(row["memory_rss_mb"]))
                mem_pct.append(float(row["memory_percent"]))
        if not timestamps:
            return self._placeholder_chart("memory_usage")
        base = timestamps[0]
        rel_time = [(t - base) / 60 for t in timestamps]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        ax1.plot(rel_time, mem_mb, color="#22c55e", linewidth=1.5)
        ax1.fill_between(rel_time, mem_mb, alpha=0.2, color="#22c55e")
        ax1.set_ylabel("Memory RSS (MB)")
        ax1.set_title("Memory Usage Over Time")
        ax1.grid(True, alpha=0.3)
        ax2.plot(rel_time, mem_pct, color="#3b82f6", linewidth=1.5)
        ax2.fill_between(rel_time, mem_pct, alpha=0.2, color="#3b82f6")
        ax2.set_xlabel("Time (minutes)")
        ax2.set_ylabel("Memory (%)")
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        return self._save("memory_usage")

    def cpu_usage_graph(self, csv_path: Path) -> Path:
        if not MATPLOTLIB_AVAILABLE:
            return self._placeholder_chart("cpu_usage")
        self._setup_style()
        import csv
        timestamps, cpu_pct = [], []
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamps.append(float(row["timestamp"]))
                cpu_pct.append(float(row["cpu_percent"]))
        if not timestamps:
            return self._placeholder_chart("cpu_usage")
        base = timestamps[0]
        rel_time = [(t - base) / 60 for t in timestamps]
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(rel_time, cpu_pct, color="#f59e0b", linewidth=1.5)
        ax.fill_between(rel_time, cpu_pct, alpha=0.2, color="#f59e0b")
        ax.set_xlabel("Time (minutes)")
        ax.set_ylabel("CPU (%)")
        ax.set_title("CPU Usage Over Time")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        return self._save("cpu_usage")

    def error_distribution(self, errors: dict[str, int | dict[str, int]]) -> Path:
        if not MATPLOTLIB_AVAILABLE:
            return self._placeholder_chart("error_distribution")
        self._setup_style()
        by_type = errors.get("by_type", {})
        if isinstance(by_type, dict) and by_type:
            labels = list(by_type.keys())
            values = list(by_type.values())
            colors = plt.cm.Reds(np.linspace(0.3, 0.8, len(labels)))
            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.barh(labels, values, color=colors)
            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                        str(val), va="center", fontsize=10)
            ax.set_xlabel("Count")
            ax.set_title("Error Distribution by Type")
            ax.grid(True, alpha=0.3, axis="x")
            fig.tight_layout()
        else:
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.text(0.5, 0.5, "No errors recorded", ha="center", va="center", fontsize=14, color="#6b7280")
            ax.set_title("Error Distribution")
        return self._save("error_distribution")

    def throughput_graph(self, counters: dict[str, int]) -> Path:
        if not MATPLOTLIB_AVAILABLE:
            return self._placeholder_chart("throughput")
        self._setup_style()
        component_calls = {k: v for k, v in counters.items() if k.startswith("component_calls.")}
        if component_calls:
            labels = [k.replace("component_calls.", "")[:15] for k in component_calls.keys()]
            values = list(component_calls.values())
            colors = plt.cm.Greens(np.linspace(0.3, 0.8, len(labels)))
            fig, ax = plt.subplots(figsize=(10, 5))
            bars = ax.bar(labels, values, color=colors)
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        str(val), ha="center", fontsize=9)
            ax.set_ylabel("Call Count")
            ax.set_title("Component Call Distribution (Throughput)")
            ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
            ax.grid(True, alpha=0.3, axis="y")
            fig.tight_layout()
        else:
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.text(0.5, 0.5, "No throughput data", ha="center", va="center", fontsize=14, color="#6b7280")
        return self._save("throughput")

    def generate_all_charts(
        self,
        latency_data: dict | None = None,
        csv_path: Path | None = None,
        errors: dict | None = None,
        counters: dict | None = None,
    ) -> list[Path]:
        paths = []
        if latency_data:
            paths.append(self.latency_histogram(latency_data))
            paths.append(self.p95_p99_chart(latency_data))
        if csv_path and csv_path.exists():
            paths.append(self.memory_usage_graph(csv_path))
            paths.append(self.cpu_usage_graph(csv_path))
        if errors:
            paths.append(self.error_distribution(errors))
        if counters:
            paths.append(self.throughput_graph(counters))
        logger.info("Generated %d charts", len(paths))
        return paths

    def _placeholder_chart(self, name: str) -> Path:
        if MATPLOTLIB_AVAILABLE:
            self._setup_style()
            fig, ax = plt.subplots(figsize=(8, 3))
            ax.text(0.5, 0.5, "Chart requires live system data", ha="center", va="center",
                    fontsize=14, color="#6b7280", transform=ax.transAxes)
            ax.set_title(name.replace("_", " ").title())
            return self._save(name)
        path = self.output_dir / f"{name}.txt"
        path.write_text(f"Placeholder for {name} chart — restart with live data to generate\n")
        return path
