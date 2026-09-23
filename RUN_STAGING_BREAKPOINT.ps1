param(
    [string]$BaseUrl
)

$ErrorActionPreference = "Stop"

Write-Host "ВАЖНО: этот сценарий только для ОТДЕЛЬНОГО staging-клона Corporation."
Write-Host "На staging в Railway должна быть переменная ALLOW_DEV_AUTH=1."
Write-Host "На production ALLOW_DEV_AUTH должен оставаться выключенным/удаленным."
Write-Host ""

$confirm = Read-Host "Напиши STAGING, если URL ниже относится к тестовой копии"
if ($confirm -ne "STAGING") {
    Write-Host "Отменено."
    exit 1
}

if (-not $BaseUrl) {
    $BaseUrl = Read-Host "URL staging FastAPI/Railway"
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
Write-Host "GAME BREAKPOINT TEST"
Write-Host "Нагрузка: 5 -> 10 -> 25 -> 50 -> 75 -> 100 -> 150 -> 200 -> 300 -> 500 VU."
Write-Host "Каждый VU = отдельный синтетический игрок."
Write-Host "Автостоп: >3% HTTP-ошибок или p95 >= 2.5 сек."
Write-Host ""

k6 run --summary-export ".\results\staging_summary.json" ".\staging_game_breakpoint.js" 2>&1 |
    Tee-Object -FilePath ".\results\staging_console.txt"

Write-Host ""
Write-Host "Тест завершен/остановлен порогом."
Write-Host "Пришли мне:"
Write-Host "  results\staging_summary.json"
Write-Host "  results\staging_console.txt"
Write-Host ""
Write-Host "И сделай скрин Railway -> FastAPI service -> Metrics за время теста:"
Write-Host "CPU, Memory, Network."
