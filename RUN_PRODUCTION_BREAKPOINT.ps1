param(
    [string]$BaseUrl = "https://corporation-game-production-862a.up.railway.app"
)

$ErrorActionPreference = "Stop"
$BaseUrl = $BaseUrl.TrimEnd('/')

Write-Host ""
Write-Host "CORPORATION - PRODUCTION BREAKPOINT TEST"
Write-Host "Target: $BaseUrl"
Write-Host ""
Write-Host "Тест НЕ трогает Telegram Bot API и НЕ изменяет игровую БД."
Write-Host "Будут запрашиваться только:"
Write-Host "  GET /"
Write-Host "  GET /static/app.js"
Write-Host "  GET /static/style.css"
Write-Host ""
Write-Host "Нагрузка: 5 -> 10 -> 25 -> 50 -> 75 -> 100 -> 150 -> 200 -> 300 VU."
Write-Host "Автостоп: >=3% ошибок или p95 >= 2.5 сек."
Write-Host ""

$answer = Read-Host "Для запуска напиши START"
if ($answer -ne "START") {
    Write-Host "Отменено."
    exit 1
}

if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) {
    Write-Host ""
    Write-Host "k6 не установлен."
    Write-Host "Выполни:"
    Write-Host "winget install k6 --source winget"
    exit 1
}

New-Item -ItemType Directory -Force -Path ".\results" | Out-Null
$env:BASE_URL = $BaseUrl

Write-Host ""
Write-Host "Запуск..."
Write-Host "Параллельно открой Railway -> FastAPI service -> Metrics."
Write-Host ""

k6 run --summary-export ".\results\production_summary.json" ".\production_breakpoint.js" 2>&1 |
    Tee-Object -FilePath ".\results\production_console.txt"

Write-Host ""
Write-Host "============================================"
Write-Host "ТЕСТ ЗАВЕРШЕН"
Write-Host "============================================"
Write-Host ""
Write-Host "Пришли ChatGPT:"
Write-Host "  results\production_summary.json"
Write-Host "  results\production_console.txt"
Write-Host "  + скрин Railway Metrics (CPU / Memory / Network)"
Write-Host ""
