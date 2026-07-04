# Halal Graph — production deploy (Windows + Docker Desktop)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "=== Halal Graph Production Deploy ===" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker not found. Install Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/" -ForegroundColor Red
    exit 1
}

$required = @("gcn_best.pt", "gat_best.pt", "rf_bundle.joblib", "feature_cols.joblib")
foreach ($f in $required) {
    if (-not (Test-Path "artifacts\models\$f")) {
        Write-Host "Missing model: artifacts\models\$f — run the training notebook first." -ForegroundColor Red
        exit 1
    }
}

if (-not (Test-Path ".env")) {
    Copy-Item ".env.production.example" ".env"
    $jwt = -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
    (Get-Content ".env") -replace "^JWT_SECRET=.*", "JWT_SECRET=$jwt" | Set-Content ".env"
    (Get-Content ".env") -replace "^NEXT_PUBLIC_API_URL=.*", "NEXT_PUBLIC_API_URL=http://localhost" | Set-Content ".env"
    (Get-Content ".env") -replace "^CORS_ORIGINS=.*", "CORS_ORIGINS=http://localhost" | Set-Content ".env"
    Write-Host "Created .env with generated JWT. Edit NEXT_PUBLIC_API_URL for your domain." -ForegroundColor Yellow
}

Write-Host "Building and starting production stack (this may take 10-15 min first time)..." -ForegroundColor Cyan
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

Write-Host "Waiting for health check..." -ForegroundColor Cyan
for ($i = 1; $i -le 36; $i++) {
    Start-Sleep -Seconds 5
    try {
        $r = Invoke-RestMethod -Uri "http://localhost/health" -TimeoutSec 5
        Write-Host "API healthy: $($r | ConvertTo-Json -Compress)" -ForegroundColor Green
        break
    } catch {
        if ($i -eq 36) {
            Write-Host "Timed out. Run: docker compose logs api" -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "=== Deploy complete ===" -ForegroundColor Green
Write-Host "Dashboard : http://localhost/"
Write-Host "Prevention: http://localhost/prevention"
Write-Host "API docs  : http://localhost/docs"
Write-Host "Login     : admin@gmail.com / Admin@12345  (change immediately!)"
