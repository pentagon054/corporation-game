param(
    [string]$BaseUrl
)

$ErrorActionPreference = "Stop"

if (-not $BaseUrl) {
    $BaseUrl = Read-Host "URL FastAPI/Railway (example: https://your-service.up.railway.app)"
}
$BaseUrl = $BaseUrl.TrimEnd('/')

if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "k6 не установлен. Выполни:"
    Write-Host "winget install k6 --source winget"
    exit 1
}

$env:BASE_URL = $BaseUrl
New-Item -ItemType Directory -Force -Path ".\results" | Out-Null

Write-Host ""
Write-Host "PUBLIC BASELINE: тестируется только GET /, без игровой БД."
Write-Host "Тест автоматически остановится при >3% HTTP-ошибок или p95 >= 2.5 сек."
Write-Host ""

k6 run --summary-export ".\results\public_summary.json" ".\public_baseline.js" 2>&1 |
    Tee-Object -FilePath ".\results\public_console.txt"

Write-Host ""
Write-Host "Готово. Пришли мне:"
Write-Host "  results\public_summary.json"
Write-Host "  results\public_console.txt"
