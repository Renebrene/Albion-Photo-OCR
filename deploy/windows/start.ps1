# Start the PhotoBAse demo stack (Docker Desktop, Windows 10).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Desktop не установлен. Скачайте: https://www.docker.com/products/docker-desktop/" -ForegroundColor Red
    exit 1
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker Desktop не запущен. Запустите его и повторите." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env.demo")) {
    Copy-Item ".env.demo.example" ".env.demo"
    Write-Host "Создан .env.demo — при необходимости смените INGEST_DB_PASSWORD." -ForegroundColor Yellow
}

New-Item -ItemType Directory -Force -Path "data", "photos" | Out-Null

Write-Host "Сборка и запуск (первый раз 15-30 минут)..." -ForegroundColor Cyan
docker compose --env-file .env.demo up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Start-Sleep -Seconds 3
docker compose --env-file .env.demo ps

Write-Host ""
Write-Host "Открывайте: http://localhost:8010" -ForegroundColor Green
Start-Process "http://localhost:8010"
