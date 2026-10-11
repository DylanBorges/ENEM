@echo off
cd /d "%~dp0"
title ENEM Intelligence - Frontend Web (Porta 3000)

echo ===================================================
echo     ENEM Intelligence - Servidor Frontend Web
echo ===================================================
echo.
echo Iniciando Next.js na porta 3000...
echo Para desligar este servidor, feche esta janela ou pressione Ctrl+C.
echo.

call npm --prefix apps/web run dev

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] O servidor frontend encerrou com codigo %ERRORLEVEL%.
    pause
)
