# Full demo reset: containers + PostgreSQL volume + local data.
# Usage: .\reset.ps1 -Force
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not $Force) {
    Write-Host "Это удалит базу и каталог .\data. Запустите с -Force, если уверены." -ForegroundColor Yellow
    exit 0
}

docker compose --env-file .env.demo down -v
if (Test-Path "data") { Remove-Item -Recurse -Force "data" }
New-Item -ItemType Directory -Force -Path "data" | Out-Null
Write-Host "Демо сброшено. Фото в .\photos не удалялись." -ForegroundColor Green
