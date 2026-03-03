@echo off
setlocal enableextensions

set "ROOT=%~dp0"
set "LOG=%ROOT%demo_start.log"

(
  echo ================================================
  echo %DATE% %TIME% - START_DEMO_CLIENTE.bat avviato
  echo ROOT=%ROOT%
  echo ================================================
) >> "%LOG%" 2>nul

REM ==============================================
REM DEMO CLIENTE - Avvio One-Click
REM Limiti demo:
REM - 1 citta: Milano
REM - 2 categorie: Ristoranti, Commercialisti
REM ==============================================

REM Se mancano Node.js o Python, apriamo le pagine di download.
REM Il cliente non deve usare PowerShell o comandi: solo installare e rilanciare questo file.

where node >nul 2>&1
if errorlevel 1 (
  echo.
  echo ================================================
  echo Manca Node.js.
  echo Si aprira' il sito ufficiale. Installa Node.js 18+,
  echo poi rilancia questo file (doppio click).
  echo ================================================
  echo.
  start "" "https://nodejs.org/"
  pause
  exit /b 1
)

where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo.
    echo ================================================
    echo Manca Python.
    echo Si aprira' il sito ufficiale. Installa Python 3.11+,
    echo poi rilancia questo file (doppio click).
    echo ================================================
    echo.
    start "" "https://www.python.org/downloads/"
    pause
    exit /b 1
  )
)

if not exist "%ROOT%START_DEMO_1CLICK.bat" (
  echo.
  echo ================================================
  echo ERRORE: non trovo START_DEMO_1CLICK.bat
  echo Percorso atteso: %ROOT%START_DEMO_1CLICK.bat
  echo Assicurati di aver estratto tutto lo ZIP.
  echo ================================================
  echo.
  echo ERRORE: START_DEMO_1CLICK.bat mancante >> "%LOG%" 2>nul
  pause
  exit /b 1
)

echo Avvio START_DEMO_1CLICK.bat... >> "%LOG%" 2>nul

REM Apri una finestra che resta aperta SEMPRE (cosi' non sparisce dopo 1 secondo)
start "DEMO - Setup & Avvio" "%ComSpec%" /k "call \"%ROOT%START_DEMO_1CLICK.bat\""

exit /b 0
