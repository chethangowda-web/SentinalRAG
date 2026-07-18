#!/bin/bash
# SentinelRAG Load Test Runner
# Requires: locust (pip install locust)

HOST=${1:-http://localhost:8000}
USERS=${2:-10}
SPAWN_RATE=${3:-2}
RUN_TIME=${4:-60}
OUTPUT_DIR=${5:-../performance}

mkdir -p "$OUTPUT_DIR"

echo "=== SentinelRAG Load Test ==="
echo "Host:      $HOST"
echo "Users:     $USERS"
echo "Rate:      $SPAWN_RATE/s"
echo "Duration:  ${RUN_TIME}s"
echo "Output:    $OUTPUT_DIR"
echo ""

locust -f locustfile.py \
    --host "$HOST" \
    --headless \
    -u "$USERS" \
    -r "$SPAWN_RATE" \
    --run-time "${RUN_TIME}s" \
    --csv "$OUTPUT_DIR/load_test_stats" \
    --only-summary \
    --html "$OUTPUT_DIR/load_test_report.html"

echo ""
echo "Load test complete. Results saved to $OUTPUT_DIR"
