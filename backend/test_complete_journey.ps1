param([switch]$Cleanup)

$env:DATABASE_URL = "sqlite+aiosqlite:///./sentinelrag.db"
$env:SECRET_KEY = "change-me-in-production-test"
$env:PORT = "8015"
$env:LOG_LEVEL = "INFO"
$env:DEEPSEEK_API_KEY = "sk-or-v1-demo-key-for-testing"
$BASE = "http://localhost:8015"

if ($Cleanup) { Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force; exit }

# Start server
$p = Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\python.exe" `
    -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8015" `
    -WorkingDirectory "$PSScriptRoot" `
    -PassThru -NoNewWindow

Write-Host "Server PID: $($p.Id)" -ForegroundColor Cyan
Write-Host "Waiting for server to start..."

$ready = $false
for ($i=0; $i -lt 90; $i++) {
    Start-Sleep 1
    try { $r = Invoke-RestMethod -Uri "$BASE/" -TimeoutSec 3 -ErrorAction Stop; $ready = $true; Write-Host "Server ready after ${i}s"; break } catch {}
}
if (-not $ready) { Write-Host "Server failed to start!" -ForegroundColor Red; exit 1 }

$pass = 0; $fail = 0
function Test-Step { param($name,$scriptBlock)
    try { $result = & $scriptBlock; Write-Host "  PASS: $name" -ForegroundColor Green; $script:pass++; return $result }
    catch { Write-Host "  FAIL: $name - $_" -ForegroundColor Red; $script:fail++; return $null }
}

# ═══════ 1. REGISTER ═══════
Write-Host "`n═══ 1. REGISTER ═══" -ForegroundColor Cyan
$regBody = @{name="Test User"; email="test@sentinelrag.com"; password="TestPass123!"} | ConvertTo-Json
$reg = Test-Step "Register" { Invoke-RestMethod -Uri "$BASE/api/v1/auth/register" -Method Post -Body $regBody -ContentType "application/json" -TimeoutSec 10 }
$tokenA = $reg.access_token; $headers = @{Authorization = "Bearer $tokenA"}

# ═══════ 2. AUTH / ME ═══════
Write-Host "`n═══ 2. AUTH PROFILE ═══" -ForegroundColor Cyan
Test-Step "GET /auth/me" { Invoke-RestMethod -Uri "$BASE/api/v1/auth/me" -Headers $headers -TimeoutSec 10 }

# ═══════ 3. HEALTH ═══════
Write-Host "`n═══ 3. HEALTH ═══" -ForegroundColor Cyan
Test-Step "GET /health" { Invoke-RestMethod -Uri "$BASE/api/v1/health" -Headers $headers -TimeoutSec 10 }

# ═══════ 4. EMPTY DASHBOARD ═══════
Write-Host "`n═══ 4. EMPTY DASHBOARD ═══" -ForegroundColor Cyan
$s1 = Test-Step "Dashboard (empty)" { Invoke-RestMethod -Uri "$BASE/api/v1/dashboard/stats" -Headers $headers -TimeoutSec 10 }
if ($s1.total_documents -eq 0) { Write-Host "  PASS: 0 documents, 0 sessions" -ForegroundColor Green; $pass++ } else { Write-Host "  FAIL: Expected 0 docs, got $($s1.total_documents)" -ForegroundColor Red; $fail++ }

# ═══════ 5. UPLOAD PDF ═══════
Write-Host "`n═══ 5. UPLOAD PDF ═══" -ForegroundColor Cyan
$pdfBytes = [System.IO.File]::ReadAllBytes("$PSScriptRoot\..\test_data\sample.pdf")
$boundary = [System.Guid]::NewGuid().ToString()
$bodyBytes = [System.Text.Encoding]::UTF8.GetBytes("--$boundary`r`nContent-Disposition: form-data; name=`"file`"; filename=`"sample.pdf`"`r`nContent-Type: application/pdf`r`n`r`n") + $pdfBytes + [System.Text.Encoding]::UTF8.GetBytes("`r`n--$boundary--`r`n")
$upload = Test-Step "Upload PDF" {
    Invoke-RestMethod -Uri "$BASE/api/v1/ingest" -Method Post `
        -Headers @{Authorization = "Bearer $tokenA"; "Content-Type" = "multipart/form-data; boundary=$boundary"} `
        -Body $bodyBytes -TimeoutSec 120
}
$docId = $upload.document_id; Write-Host "  Doc ID: $docId"

# ═══════ 6. LIST DOCUMENTS ═══════
Write-Host "`n═══ 6. LIST DOCUMENTS ═══" -ForegroundColor Cyan
$docs = Test-Step "GET /documents" { Invoke-RestMethod -Uri "$BASE/api/v1/documents" -Headers $headers -TimeoutSec 10 }
if ($docs.Count -gt 0) { Write-Host "  PASS: $($docs.Count) document(s)" -ForegroundColor Green; $pass++ } else { Write-Host "  FAIL: No documents" -ForegroundColor Red; $fail++ }

# ═══════ 7. WAIT FOR PROCESSING ═══════
Write-Host "`n═══ 7. WAIT FOR PROCESSING ═══" -ForegroundColor Cyan
$completed = $false
for ($i=0; $i -lt 60; $i++) {
    Start-Sleep 2
    try {
        $dd = Invoke-RestMethod -Uri "$BASE/api/v1/documents/$docId" -Headers $headers -TimeoutSec 5
        if ($dd.status -eq "completed") { $completed = $true; Write-Host "  Completed after ~$(($i+1)*2)s: $($dd.pages)p $($dd.word_count)w $($dd.chunk_count)c"; $pass++; break }
        elseif ($dd.status -eq "failed") { Write-Host "  FAIL: Processing failed" -ForegroundColor Red; $fail++; break }
    } catch {}
}
if (-not $completed) { Write-Host "  FAIL: Not completed in time" -ForegroundColor Red; $fail++ }

# ═══════ 8. DASHBOARD AFTER UPLOAD ═══════
Write-Host "`n═══ 8. DASHBOARD AFTER UPLOAD ═══" -ForegroundColor Cyan
$s2 = Test-Step "Dashboard stats" { Invoke-RestMethod -Uri "$BASE/api/v1/dashboard/stats" -Headers $headers -TimeoutSec 10 }
if ($s2.total_documents -gt 0) { Write-Host "  PASS: $($s2.total_documents) docs, $($s2.total_chunks) chunks" -ForegroundColor Green; $pass++ } else { Write-Host "  FAIL: No data" -ForegroundColor Red; $fail++ }

# ═══════ 9. CHAT ═══════
Write-Host "`n═══ 9. CHAT ═══" -ForegroundColor Cyan
$chatBody = @{question = "What was the revenue in Q4 2025?"} | ConvertTo-Json
$chatResp = Test-Step "POST /chat" {
    Invoke-RestMethod -Uri "$BASE/api/v1/chat" -Method Post -Body $chatBody -ContentType "application/json" -Headers $headers -TimeoutSec 120
}
if ($chatResp.answer) {
    $a = $chatResp.answer; $a = $a.Substring(0, [Math]::Min(150, $a.Length))
    Write-Host "  Answer: $a..." -ForegroundColor Yellow
    Write-Host "  Confidence: $($chatResp.confidence)% ($($chatResp.confidence_level))"
    $pass++
} else { Write-Host "  FAIL: No answer" -ForegroundColor Red; $fail++ }

# ═══════ 10. LOGOUT & RE-LOGIN ═══════
Write-Host "`n═══ 10. LOGOUT & RE-LOGIN ═══" -ForegroundColor Cyan
Test-Step "POST /auth/logout" { Invoke-RestMethod -Uri "$BASE/api/v1/auth/logout" -Method Post -Headers $headers -TimeoutSec 10 }
$loginBody = @{email="test@sentinelrag.com"; password="TestPass123!"} | ConvertTo-Json
$login2 = Test-Step "POST /auth/login" { Invoke-RestMethod -Uri "$BASE/api/v1/auth/login" -Method Post -Body $loginBody -ContentType "application/json" -TimeoutSec 10 }
$headers2 = @{Authorization = "Bearer $($login2.access_token)"}
$s3 = Test-Step "Dashboard persists" { Invoke-RestMethod -Uri "$BASE/api/v1/dashboard/stats" -Headers $headers2 -TimeoutSec 10 }
if ($s3.total_documents -gt 0) { Write-Host "  PASS: $($s3.total_documents) docs persist" -ForegroundColor Green; $pass++ } else { Write-Host "  FAIL: Data lost" -ForegroundColor Red; $fail++ }

# ═══════ 11. WRONG PASSWORD ═══════
Write-Host "`n═══ 11. SECURITY ═══" -ForegroundColor Cyan
try { $badBody = @{email="test@sentinelrag.com"; password="wrong"} | ConvertTo-Json; Invoke-RestMethod -Uri "$BASE/api/v1/auth/login" -Method Post -Body $badBody -ContentType "application/json" -TimeoutSec 10; Write-Host "  FAIL: Wrong password OK" -ForegroundColor Red; $fail++ }
catch { Write-Host "  PASS: Wrong password rejected" -ForegroundColor Green; $pass++ }

# ═══════ 12. REGISTER DUPLICATE ═══════
Write-Host "`n═══ 12. DUPLICATE REGISTER ═══" -ForegroundColor Cyan
try { Invoke-RestMethod -Uri "$BASE/api/v1/auth/register" -Method Post -Body $regBody -ContentType "application/json" -TimeoutSec 10; Write-Host "  FAIL: Duplicate registered" -ForegroundColor Red; $fail++ }
catch { if ($_.Exception.Response.StatusCode.value__ -eq 409) { Write-Host "  PASS: Duplicate rejected (409)" -ForegroundColor Green; $pass++ } else { Write-Host "  FAIL: Got $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red; $fail++ } }

# ═══════ RESULTS ═══════
Write-Host "`n═════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  RESULTS: $pass passed, $fail failed" -ForegroundColor $(if ($fail -eq 0) {"Green"} else {"Red"})
Write-Host "═════════════════════════════════════" -ForegroundColor Cyan

$p.Kill()
exit $fail
