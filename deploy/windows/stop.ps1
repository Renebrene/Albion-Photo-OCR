# Stop the demo stack; data and database volume are kept.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

docker compose --env-file .env.demo down
Write-Host "Остановлено. Данные в .\data и томе pgdata сохранены." -ForegroundColor Green
