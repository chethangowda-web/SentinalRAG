pytest_plugins = ["tests.conftest"]


def pytest_benchmark_scale_item(config, item, val, columns, key):
    if key == "avg":
        columns[0] = "Avg (ms)"
    elif key == "min":
        columns[0] = "Min (ms)"
    elif key == "max":
        columns[0] = "Max (ms)"
    elif key == "p50":
        columns[0] = "P50 (ms)"
    elif key == "p95":
        columns[0] = "P95 (ms)"
    elif key == "p99":
        columns[0] = "P99 (ms)"
    return val
