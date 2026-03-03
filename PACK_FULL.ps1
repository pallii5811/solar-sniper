$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$timestamp = Get-Date -Format 'yyyyMMdd_HHmm'
$packageName = "LeadGen_FULL_$timestamp"
$staging = Join-Path $root "_full_staging\$packageName"
$outDir = Join-Path $root "_full_dist"
$zipPath = Join-Path $outDir ("$packageName.zip")

New-Item -ItemType Directory -Force -Path $staging | Out-Null
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

function Copy-Tree($srcRel, $dstRel) {
  $src = Join-Path $root $srcRel
  $dst = Join-Path $staging $dstRel
  if (-not (Test-Path $src)) { throw "Missing: $srcRel" }
  New-Item -ItemType Directory -Force -Path $dst | Out-Null

  if ($srcRel -eq 'frontend') {
    $excludeDirs = @(
      'node_modules',
      '.next',
      '.turbo',
      '.cache',
      '.parcel-cache',
      'out'
    )
    $xd = @()
    foreach ($d in $excludeDirs) { $xd += @('/XD', (Join-Path $src $d)) }

    $args = @(
      $src,
      $dst,
      '/E',
      '/NFL','/NDL','/NJH','/NJS','/NS','/NC',
      '/R:1','/W:1'
    ) + $xd

    & robocopy @args | Out-Null
    $rc = $LASTEXITCODE
    if ($rc -ge 8) { throw "robocopy frontend fallito (code=$rc)" }
  } else {
    Copy-Item -Path (Join-Path $src '*') -Destination $dst -Recurse -Force
  }
}

Copy-Tree 'backend' 'backend'
Copy-Tree 'frontend' 'frontend'

Copy-Item -Path (Join-Path $root 'START_SOFTWARE.bat') -Destination $staging -Force
Copy-Item -Path (Join-Path $root 'FULL_README.txt') -Destination $staging -Force

$removePaths = @(
  'frontend\node_modules',
  'frontend\.next',
  'frontend\.turbo',
  'frontend\.cache',
  'frontend\.parcel-cache',
  'frontend\out',
  '.venv',
  'start_software.log',
  'backend_out.log',
  'backend_err.log',
  'frontend_out.log',
  'frontend_err.log'
)
foreach ($rel in $removePaths) {
  $p = Join-Path $staging $rel
  if (Test-Path $p) {
    Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue
  }
}

Get-ChildItem -Path $staging -Recurse -Force -File -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -in @('.env', '.env.local', '.env.development.local', '.env.production.local') } |
  ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue }

if (Test-Path $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zipPath -Force

$hashPath = $zipPath + '.sha256.txt'
$hash = (Get-FileHash -Algorithm SHA256 -Path $zipPath).Hash
Set-Content -Path $hashPath -Value $hash -Encoding ascii

Write-Host "OK: creato pacchetto FULL" -ForegroundColor Green
Write-Host "ZIP: $zipPath"
Write-Host "SHA256: $hashPath"
