param(
    [switch]$Docker
)

if ($Docker) {
    Write-Host "Starting SentinelRAG with Docker..." -ForegroundColor Green
    docker compose up --build -d
    Write-Host "Services starting. Run 'docker compose logs -f' to follow." -ForegroundColor Green
    exit
}

Write-Host "Setting up SentinelRAG development environment..." -ForegroundColor Green

# Backend setup
Write-Host "`n[1/2] Setting up backend..." -ForegroundColor Cyan
Push-Location backend
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item ..\.env.example .env -ErrorAction SilentlyContinue
Pop-Location

# Frontend setup
Write-Host "`n[2/2] Setting up frontend..." -ForegroundColor Cyan
Push-Location frontend
npm install
Pop-Location

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "Run 'docker compose up --build' for full stack or use the scripts below:" -ForegroundColor Yellow
Write-Host "  Backend:  cd backend; .\.venv\Scripts\uvicorn app.main:app --reload"
Write-Host "  Frontend: cd frontend; npm run dev"
