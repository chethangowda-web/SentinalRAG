# SentinelRAG Load Test Runner
# Requires: locust (pip install locust)

param(
    [string]$Host = "http://localhost:8000",
    [int]$Users = 10,
    [int]$SpawnRate = 2,
    [int]$RunTime = 60,
    [string]$OutputDir = "../performance"
)

$OutputFile = Join-Path $OutputDir "load_test_results.json"
$CsvFile = Join-Path $OutputDir "load_test_stats.csv"

Write-Host "=== SentinelRAG Load Test ===" -ForegroundColor Green
Write-Host "Host:      $Host"
Write-Host "Users:     $Users"
Write-Host "Rate:      $SpawnRate/s"
Write-Host "Duration:  ${RunTime}s"
Write-Host "Output:    $OutputFile"
Write-Host ""

# Ensure output dir exists
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# Run locust in headless mode
locust -f locustfile.py `
    --host $Host `
    --headless `
    -u $Users `
    -r $SpawnRate `
    --run-time ${RunTime}s `
    --csv $CsvFile `
    --only-summary `
    --html $OutputFile.Replace(".json", "_report.html")

Write-Host ""
Write-Host "Load test complete. Results saved to $OutputDir" -ForegroundColor Green
