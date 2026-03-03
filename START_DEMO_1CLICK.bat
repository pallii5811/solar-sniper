@echo off
setlocal enableextensions enabledelayedexpansion

set "ROOT=%~dp0"
title DEMO - Setup ^& Avvio

echo ================================================
echo DEMO - Lead Generation ^& Audit Machine
echo Avvio automatico (1 click)
echo ================================================
echo(

REM ------------------------------------------------
REM DEMO CONFIG (modifica qui se vuoi cambiare demo)
REM ------------------------------------------------
set "DEMO_CITY=Milano"
set "DEMO_CATEGORIES=Ristoranti,Commercialisti"

set "DEMO_BACKEND_PORT=8001"
set "DEMO_FRONTEND_PORT=3001"

set "DEMO_MAX_RESULTS=10"

set "NEXT_PUBLIC_DEMO_CITY=%DEMO_CITY%"
set "NEXT_PUBLIC_DEMO_CATEGORIES=%DEMO_CATEGORIES%"
set "NEXT_PUBLIC_BACKEND_URL=http://localhost:%DEMO_BACKEND_PORT%"
set "PORT=%DEMO_FRONTEND_PORT%"

echo Demo impostata su:
echo - Citta: %DEMO_CITY%
echo - Categorie: %DEMO_CATEGORIES%
echo(

REM ------------------------------------------------
REM Prerequisiti
REM ------------------------------------------------
where node >nul 2>&1
if errorlevel 1 goto :NODE_MISSING

where py >nul 2>&1
if errorlevel 1 where python >nul 2>&1
if errorlevel 1 goto :PY_MISSING

REM ------------------------------------------------
REM Backend: venv + pip + playwright
REM ------------------------------------------------
set "VENV_DIR=%ROOT%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PY%" (
  echo [1/5] Creo ambiente virtuale Python...
  py -3 -m venv "%VENV_DIR%" >nul 2>&1
  if errorlevel 1 (
    python -m venv "%VENV_DIR%" || goto :FAIL
  )
)

echo [2/5] Installo dipendenze backend (pip)...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel || goto :FAIL
"%VENV_PY%" -m pip install -r "%ROOT%backend\requirements.txt" || goto :FAIL

echo [3/5] Installo browser Playwright (Chromium)...
"%VENV_PY%" -m playwright install chromium || goto :FAIL

REM ------------------------------------------------
REM Frontend: npm
REM ------------------------------------------------
echo [4/5] Installo dipendenze frontend (npm)...
pushd "%ROOT%frontend" || goto :FAIL
if exist "package-lock.json" (
  npm ci || goto :NPM_INSTALL_FALLBACK
) else (
  npm install || goto :FAIL
)
popd

goto :START_SERVICES

REM ------------------------------------------------
REM Avvio servizi
REM ------------------------------------------------
:START_SERVICES
echo [5/5] Avvio backend e frontend...

start "Backend - FastAPI (DEMO)" /min cmd /k "pushd \"%ROOT%\" ^& set DEMO_CITY=%DEMO_CITY% ^& set DEMO_CATEGORIES=%DEMO_CATEGORIES% ^& set DEMO_MAX_RESULTS=%DEMO_MAX_RESULTS% ^& \"%VENV_PY%\" -m uvicorn backend.main:app --port %DEMO_BACKEND_PORT%"
start "Frontend - Next.js (DEMO)" /min cmd /k "pushd \"%ROOT%\" ^& set NEXT_PUBLIC_DEMO_CITY=%DEMO_CITY% ^& set NEXT_PUBLIC_DEMO_CATEGORIES=%DEMO_CATEGORIES% ^& set NEXT_PUBLIC_BACKEND_URL=%NEXT_PUBLIC_BACKEND_URL% ^& set PORT=%PORT% ^& pushd \"%ROOT%frontend\" ^&^& npm run dev"

echo(
echo Attendo che il software sia pronto su http://localhost:%DEMO_FRONTEND_PORT% ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "
  $timeoutSeconds = 90;
  $sw = [Diagnostics.Stopwatch]::StartNew();
  while ($sw.Elapsed.TotalSeconds -lt $timeoutSeconds) {
    try {
      if (Test-NetConnection -ComputerName 'localhost' -Port %DEMO_FRONTEND_PORT% -InformationLevel Quiet) { break }
    } catch { }
    Start-Sleep -Milliseconds 500;
  }
" >nul 2>&1

start "" "http://localhost:%DEMO_FRONTEND_PORT%" >nul 2>&1

echo(
echo ================================================
echo DEMO pronta.
echo Se il browser non si e' aperto, vai su:
echo http://localhost:%DEMO_FRONTEND_PORT%
echo ================================================
echo(
echo Puoi chiudere questa finestra. (Backend e Frontend restano attivi)
echo(
pause
exit /b 0

:NPM_INSTALL_FALLBACK
npm install || goto :FAIL
popd
goto :START_SERVICES

:NODE_MISSING
echo ================================================
echo Manca Node.js.
echo Si aprira' il sito ufficiale: installa Node.js 18+
echo poi rilancia questo file (doppio click).
echo ================================================
start "" "https://nodejs.org/"
echo(
pause
exit /b 1

:PY_MISSING
echo ================================================
echo Manca Python.
echo Si aprira' il sito ufficiale: installa Python 3.11+
echo poi rilancia questo file (doppio click).
echo ================================================
start "" "https://www.python.org/downloads/"
echo(
pause
exit /b 1

:FAIL
echo(
echo ================================================
echo ERRORE durante installazione/avvio.
echo Chiudi e riprova. Se l'errore persiste, invia screenshot.
echo ================================================
echo(
pause
exit /b 1
