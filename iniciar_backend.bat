@echo off
cd /d "%~dp0"
title ENEM Intelligence - Backend API (Porta 8000)

echo ===================================================
echo     ENEM Intelligence - Servidor Backend API
echo ===================================================
echo.
echo Iniciando FastAPI / Uvicorn na porta 8000...
echo Para desligar este servidor, feche esta janela ou pressione Ctrl+C.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Python nao encontrado em .venv\Scripts\python.exe
    pause
    exit /b 1
)

.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir services/api --host 0.0.0.0 --port 8000

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] O servidor backend encerrou com codigo %ERRORLEVEL%.
    pause
)
