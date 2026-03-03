@echo off
setlocal
title LeadGen Launcher
cd /d "%~dp0"

echo ==========================================
echo AVVIO FORZATO SISTEMA
echo ==========================================

echo.
echo [1/3] Configurazione Motore...

echo Avvio Backend in nuova finestra...
start "MOTORE BACKEND" cmd /k "cd backend && pip install -r requirements.txt --quiet && python -m uvicorn main:app --port 8000"

echo.
echo [2/3] Attendo avvio del server (5 secondi)...
timeout /t 5 >nul

echo.
echo [3/3] Avvio Interfaccia...

start http://localhost:3000

start "INTERFACCIA" cmd /k "cd frontend && set NEXT_PUBLIC_BACKEND_URL=http://127.0.0.1:8000 && npm install --quiet && npm run dev"

pause
