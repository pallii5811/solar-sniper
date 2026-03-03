$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$log = Join-Path $root 'demo_start.log'
[System.IO.File]::WriteAllText(
  $log,
  "===============================================`r`n" +
  "$([DateTime]::Now.ToString('yyyy-MM-dd HH:mm:ss')) - START_DEMO_1CLICK.ps1`r`n" +
  "ROOT=$root`r`n" +
  "===============================================`r`n",
  [System.Text.UTF8Encoding]::new($false)
)

function Log($msg) {
  $line = [string]$msg
  [System.IO.File]::AppendAllText(
    $log,
    $line + "`r`n",
    [System.Text.UTF8Encoding]::new($false)
  )
  Write-Host $line
}

function Test-PortOpen {
  param(
    [string]$hostname,
    [int]$port,
    [int]$timeoutMs = 400
  )
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $iar = $client.BeginConnect($hostname, $port, $null, $null)
    if (-not $iar.AsyncWaitHandle.WaitOne($timeoutMs, $false)) {
      $client.Close()
      return $false
    }
    $client.EndConnect($iar)
    $client.Close()
    return $true
  } catch {
    return $false
  }
}

try {

function Run-Npm {
  param(
    [string]$cwd,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$npmArgs
  )
  $npmCmd = Get-Command 'npm.cmd' -ErrorAction SilentlyContinue
  if (-not $npmCmd) {
    $npmCmd = Get-Command 'npm' -ErrorAction SilentlyContinue
  }
  if (-not $npmCmd) {
    throw 'npm non trovato (node installato?)'
  }

  function Escape-CmdArg([string]$s) {
    if ($null -eq $s) { return '""' }
    $needsQuotes = ($s -match '[\s"&<>|^()]')
    $v = $s -replace '"', '""'
    if ($needsQuotes) { return '"' + $v + '"' }
    return $v
  }

  $tmpOut = Join-Path $env:TEMP ("demo_npm_out_{0}.log" -f ([Guid]::NewGuid().ToString('n')))
  $tmpErr = Join-Path $env:TEMP ("demo_npm_err_{0}.log" -f ([Guid]::NewGuid().ToString('n')))
  try {
    # On Windows, npm may resolve to a PowerShell shim (npm.ps1). Running it directly can fail with: "%1 is not a valid Win32 application".
    # Use cmd.exe to execute npm.cmd reliably.
    $npmExe = $npmCmd.Source
    $argsPart = (($npmArgs | ForEach-Object { Escape-CmdArg $_ }) -join ' ')

    # IMPORTANT: cmd.exe has special quoting rules.
    # To run an executable with spaces reliably, you must wrap the whole command in quotes,
    # and also quote the executable path inside, like:
    # cmd /s /c ""C:\Program Files\nodejs\npm.cmd" ci"
    $npmExeCmd = $npmExe -replace '"', '""'
    $cmdLine = '""' + $npmExeCmd + '" ' + $argsPart + '"'

    $p = Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d','/s','/c', $cmdLine) -WorkingDirectory $cwd -NoNewWindow -Wait -PassThru -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr

    if (Test-Path $tmpOut) {
      Get-Content -Path $tmpOut -ErrorAction SilentlyContinue | ForEach-Object { Log $_ }
    }
    if (Test-Path $tmpErr) {
      Get-Content -Path $tmpErr -ErrorAction SilentlyContinue | ForEach-Object { Log $_ }
    }

    return [int]$p.ExitCode
  } finally {
    try { Remove-Item -LiteralPath $tmpOut -Force -ErrorAction SilentlyContinue } catch { }
    try { Remove-Item -LiteralPath $tmpErr -Force -ErrorAction SilentlyContinue } catch { }
  }
}

function Run-Python {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$pyArgs
  )
  & $venvPy @pyArgs 2>&1 | ForEach-Object { Log $_ }
  return $LASTEXITCODE
}

# -----------------
# DEMO CONFIG
# -----------------
$demoCity = 'Milano'
$demoCategories = 'Ristoranti,Commercialisti'

$demoBackendPort = 8001
$demoFrontendPort = 3001

$env:DEMO_CITY = $demoCity
$env:DEMO_CATEGORIES = $demoCategories
$env:DEMO_MAX_RESULTS = '10'
$env:NEXT_PUBLIC_DEMO_CITY = $demoCity
$env:NEXT_PUBLIC_DEMO_CATEGORIES = $demoCategories
$env:NEXT_PUBLIC_BACKEND_URL = "http://localhost:$demoBackendPort"

Log "DEMO: City=$demoCity"
Log "DEMO: Categories=$demoCategories"
Log "DEMO ports: backend=$demoBackendPort frontend=$demoFrontendPort"

if (Test-PortOpen '127.0.0.1' $demoFrontendPort) {
  throw "Porta $demoFrontendPort occupata. Chiudi il software completo (o qualsiasi Next) e rilancia la DEMO."
}
if (Test-PortOpen '127.0.0.1' $demoBackendPort) {
  throw "Porta $demoBackendPort occupata. Chiudi il software completo (o qualsiasi backend) e rilancia la DEMO."
}

# -----------------
# Prerequisiti
# -----------------
function Require-Command($name, $url) {
  $cmd = Get-Command $name -ErrorAction SilentlyContinue
  if (-not $cmd) {
    Log "Manca $name. Apro: $url"
    Start-Process $url
    throw "Manca $name. Installa e rilancia."
  }
}

Require-Command 'node' 'https://nodejs.org/'

$pyCmd = Get-Command 'py' -ErrorAction SilentlyContinue
if (-not $pyCmd) {
  $pyCmd = Get-Command 'python' -ErrorAction SilentlyContinue
  if (-not $pyCmd) {
    Log "Manca Python. Apro: https://www.python.org/downloads/"
    Start-Process 'https://www.python.org/downloads/'
    throw "Manca Python. Installa e rilancia."
  }
}

# -----------------
# Backend setup
# -----------------
$venvDir = Join-Path $root '.venv'
$venvPy = Join-Path $venvDir 'Scripts\python.exe'

$reqPath = Join-Path $root 'backend\requirements.txt'
$reqStampPath = Join-Path $venvDir '.requirements.sha256'
$msPlaywrightDir = Join-Path $env:LOCALAPPDATA 'ms-playwright'

Log "Python venv: $venvPy"

if (-not (Test-Path $venvPy)) {
  Log '[1/5] Creo ambiente virtuale Python...'
  if (Get-Command 'py' -ErrorAction SilentlyContinue) {
    & py -3 -m venv $venvDir 2>&1 | ForEach-Object { Log $_ }
  } else {
    & python -m venv $venvDir 2>&1 | ForEach-Object { Log $_ }
  }
}

Log '[2/5] Verifico dipendenze backend (pip)...'
$reqHash = (Get-FileHash -Algorithm SHA256 -Path $reqPath).Hash
$needPip = $true
if (Test-Path $reqStampPath) {
  try {
    $prev = (Get-Content -Path $reqStampPath -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($prev -eq $reqHash) { $needPip = $false }
  } catch { }
}

if ($needPip) {
  Log 'Install richiesto: requirements.txt cambiato o prima esecuzione.'
  if ((Run-Python -m pip install --upgrade pip setuptools wheel) -ne 0) { throw 'pip upgrade fallito' }
  if ((Run-Python -m pip install -r $reqPath) -ne 0) { throw 'pip install fallito' }
  try { Set-Content -Path $reqStampPath -Value $reqHash -Encoding ascii } catch { }
} else {
  Log 'Backend OK: requirements gia'' installati, salto pip install.'
}

Log '[3/5] Verifico browser Playwright (Chromium)...'
$hasChromium = $false
try {
  if (Test-Path $msPlaywrightDir) {
    $hasChromium = (Get-ChildItem -Path $msPlaywrightDir -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like 'chromium-*' } | Select-Object -First 1) -ne $null
  }
} catch { $hasChromium = $false }

if (-not $hasChromium) {
  Log 'Playwright: Chromium non trovato, installo...'
  if ((Run-Python -m playwright install chromium) -ne 0) { throw 'playwright install fallito' }
} else {
  Log 'Playwright OK: Chromium gia'' presente, salto install.'
}

# -----------------
# Frontend setup
# -----------------
Log '[4/5] Installo dipendenze frontend (npm)...'
$frontendDir = Join-Path $root 'frontend'
$nextCmd = Join-Path $frontendDir 'node_modules\.bin\next.cmd'
$needNpm = -not (Test-Path $nextCmd)
if (-not $needNpm) {
  Log 'Frontend OK: Next trovato, salto install npm.'
} else {
  $hasLock = Test-Path (Join-Path $frontendDir 'package-lock.json')
  $installCmd = if ($hasLock) { 'ci' } else { 'install' }
  $code = Run-Npm $frontendDir $installCmd
  if ($code -ne 0) {
    $staging = Join-Path $frontendDir 'node_modules\.staging'
    if (Test-Path $staging) {
      Log 'npm fallito: provo cleanup node_modules\.staging e retry...'
      try {
        Remove-Item -LiteralPath $staging -Recurse -Force -ErrorAction SilentlyContinue
      } catch { }
      $code = Run-Npm $frontendDir $installCmd
    }
  }
  if ($code -ne 0) {
    Log 'npm fallito in modo persistente. Possibile causa: file bloccati (ENOTEMPTY/EPERM).'
    Log 'Chiudi tutte le finestre Node/Next, terminali, VSCode che stanno usando frontend e riprova.'
    throw "npm $installCmd fallito (exit=$code)"
  }
  if (-not (Test-Path $nextCmd)) {
    throw 'Install npm completata ma Next non trovato (node_modules corrotto).'
  }
}

# -----------------
# Avvio servizi
# -----------------
Log '[5/5] Avvio backend e frontend...'

$backendOutLog = Join-Path $root 'demo_backend_out.log'
$backendErrLog = Join-Path $root 'demo_backend_err.log'
$frontendOutLog = Join-Path $root 'demo_frontend_out.log'
$frontendErrLog = Join-Path $root 'demo_frontend_err.log'

try {
  Remove-Item -LiteralPath $backendOutLog -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $backendErrLog -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $frontendOutLog -Force -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $frontendErrLog -Force -ErrorAction SilentlyContinue
} catch { }

$demoCityPs = $demoCity.Replace("'", "''")
$demoCategoriesPs = $demoCategories.Replace("'", "''")
$backendUrl = "http://localhost:$demoBackendPort"
$backendUrlPs = $backendUrl.Replace("'", "''")

$backendArgs = @(
  '-NoProfile','-ExecutionPolicy','Bypass','-Command',
  "cd '$root'; `$env:DEMO_CITY='$demoCityPs'; `$env:DEMO_CATEGORIES='$demoCategoriesPs'; `$env:DEMO_MAX_RESULTS='10'; & '$venvPy' -m uvicorn backend.main:app --port $demoBackendPort"
)
Start-Process -FilePath 'powershell.exe' -ArgumentList $backendArgs -WindowStyle Minimized -RedirectStandardOutput $backendOutLog -RedirectStandardError $backendErrLog | Out-Null

$frontendArgs = @(
  '-NoProfile','-ExecutionPolicy','Bypass','-Command',
  "cd '$frontendDir'; `$env:NEXT_PUBLIC_DEMO_CITY='$demoCityPs'; `$env:NEXT_PUBLIC_DEMO_CATEGORIES='$demoCategoriesPs'; `$env:NEXT_PUBLIC_BACKEND_URL='$backendUrlPs'; `$env:PORT='$demoFrontendPort'; npx --no-install next dev --port $demoFrontendPort"
)
Start-Process -FilePath 'powershell.exe' -ArgumentList $frontendArgs -WindowStyle Minimized -RedirectStandardOutput $frontendOutLog -RedirectStandardError $frontendErrLog | Out-Null

Log "Attendo che il software sia pronto su http://localhost:$demoFrontendPort ..."
$timeoutSeconds = 180
$sw = [Diagnostics.Stopwatch]::StartNew()
while ($sw.Elapsed.TotalSeconds -lt $timeoutSeconds) {
  try {
    if (Test-PortOpen '127.0.0.1' $demoFrontendPort) { break }
  } catch { }
  Start-Sleep -Milliseconds 500
}

if (-not (Test-PortOpen '127.0.0.1' $demoFrontendPort)) {
  Log "ERRORE: frontend DEMO non avviato su porta $demoFrontendPort entro $timeoutSeconds secondi."
  Log "Guarda questi file per l'errore preciso:"
  Log "- $frontendOutLog"
  Log "- $frontendErrLog"
  Log "- $backendOutLog"
  Log "- $backendErrLog"
  try {
    Log '--- Ultime righe demo_frontend.log ---'
    Get-Content -Path $frontendErrLog -Tail 30 -ErrorAction SilentlyContinue | ForEach-Object { Log $_ }
  } catch { }
  throw "Frontend DEMO non avviato"
}

Start-Process "http://localhost:$demoFrontendPort" | Out-Null

Log "DEMO pronta. Se non si apre il browser: http://localhost:$demoFrontendPort"
Log "Log file: $log"

Write-Host ''
Write-Host '==============================================='
Write-Host 'DEMO pronta.'
Write-Host 'Se il browser non si e'' aperto, vai su:'
Write-Host "http://localhost:$demoFrontendPort"
Write-Host "Log: $log"
Write-Host '==============================================='
Write-Host ''
Write-Host 'Premi INVIO per chiudere questa finestra (backend/frontend restano attivi).'
[void][Console]::ReadLine()
} catch {
  $err = $_.Exception.Message
  Log "ERRORE: $err"
  Write-Host ''
  Write-Host '==============================================='
  Write-Host "ERRORE durante l'avvio DEMO."
  Write-Host $err
  Write-Host "Log: $log"
  Write-Host '==============================================='
  Write-Host ''
  Write-Host 'Premi INVIO per chiudere questa finestra.'
  [void][Console]::ReadLine()
  exit 1
}
