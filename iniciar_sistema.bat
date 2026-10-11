@echo off
cd /d "%~dp0"
title ENEM Intelligence - Inicializador

echo ===================================================
echo     Iniciando Plataforma ENEM Intelligence
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual .venv nao encontrado em %~dp0
    pause
    exit /b 1
)

echo [1/2] Abrindo servidor Backend API (Porta 8000)...
start "ENEM Backend API" cmd /c "%~dp0iniciar_backend.bat"

echo [2/2] Abrindo servidor Frontend Web (Porta 3000)...
start "ENEM Frontend Web" cmd /c "%~dp0iniciar_frontend.bat"

echo.
echo ===================================================
echo  Servidores iniciados em janelas proprias!
echo.
echo  Acesse:
echo  * Frontend: http://localhost:3000
echo  * Backend:  http://localhost:8000
echo  * Swagger:  http://localhost:8000/docs
echo ===================================================
echo IMPORTANTE: Deixe as janelas abertas enquanto usar o sistema.
echo.
pause
