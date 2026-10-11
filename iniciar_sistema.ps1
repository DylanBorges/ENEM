# Script de inicializacao do ENEM Intelligence
Set-Location -Path $PSScriptRoot

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "    Iniciando Plataforma ENEM Intelligence        " -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "$PSScriptRoot\.venv\Scripts\python.exe")) {
    Write-Host "[ERRO] Ambiente virtual .venv nao encontrado em $PSScriptRoot" -ForegroundColor Red
    pause
    exit 1
}

Write-Host "[1/2] Iniciando Servidor Backend FastAPI (Porta 8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; .\.venv\Scripts\python -m uvicorn app.main:app --app-dir services/api --host 0.0.0.0 --port 8000"

Write-Host "[2/2] Iniciando Servidor Frontend Next.js (Porta 3000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; npm --prefix apps/web run dev"

Write-Host ""
Write-Host "===================================================" -ForegroundColor Green
Write-Host " Servidores iniciados em janelas dedicadas!" -ForegroundColor Green
Write-Host " Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host " Backend:  http://localhost:8000" -ForegroundColor Green
Write-Host " Swagger:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green
Write-Host "Mantenha as janelas do terminal abertas enquanto estiver utilizando."
Start-Sleep -Seconds 5
