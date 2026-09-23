param(
    [string]$BaseUrl = "https://corporation-game-production-862a.up.railway.app"
)

# Do NOT use Stop here: k6 writes warnings such as request timeouts to stderr.
$ErrorActionPreference = "Continue"

$BaseUrl = $BaseUrl.TrimEnd('/')

Write-Host ""
Write-Host "CORPORATION - PRODUCTION LOAD TEST v3"
Write-Host "Target: $BaseUrl"
Write-Host ""
Write-Host "Без игровых POST-запросов и без изменений базы."
Write-Host "Статика загружается один раз на VU; затем основная нагрузка идет на GET /."
Write-Host ""
Write-Host "Ramp: 5 -> 10 -> 25 -> 50 -> 75 -> 100 -> 150 -> 200 -> 300 VU"
Write-Host "Autostop: >=3% HTTP failures or p95 >= 2.5 sec."
Write-Host ""

$answer = Read-Host "Для запуска напиши START"
if ($answer -ne "START") {
    Write-Host "Отменено."
    exit 1
}

if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) {
    Write-Host "k6 не найден. Выполни: winget install k6 --source winget"
    exit 1
}

New-Item -ItemType Directory -Force -Path ".\results" | Out-Null
$env:BASE_URL = $BaseUrl

# Prevent Windows PowerShell from terminating on k6 stderr warnings.
$oldEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"

& k6 run `
  --summary-export ".\results\production_summary.json" `
  ".\production_breakpoint_v3.js" 2>&1 |
  Tee-Object -FilePath ".\results\production_console.txt"

$k6Exit = $LASTEXITCODE
$ErrorActionPreference = $oldEap

Write-Host ""
Write-Host "============================================"
Write-Host "K6 FINISHED"
Write-Host "Exit code: $k6Exit"
Write-Host "============================================"
Write-Host ""

if (Test-Path ".\results\production_summary.json") {
    Write-Host "OK: results\production_summary.json"
} else {
    Write-Host "WARNING: summary JSON was not created."
}

if (Test-Path ".\results\production_console.txt") {
    Write-Host "OK: results\production_console.txt"
}

Write-Host ""
Write-Host "Пришли оба файла + новый скрин Railway Metrics."
