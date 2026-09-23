param(
    [string]$BaseUrl = "https://corporation-game-production-862a.up.railway.app"
)

$ErrorActionPreference = "Continue"
$BaseUrl = $BaseUrl.TrimEnd('/')

Write-Host ""
Write-Host "CORPORATION - GAME READ LOAD TEST v4"
Write-Host "Production: $BaseUrl"
Write-Host ""
Write-Host "Нагрузка:"
Write-Host "10 -> 25 -> 50 -> 100 -> 200 -> 300 -> 500 -> 750 -> 1000 VU"
Write-Host "Финальные 1000 VU удерживаются 30 секунд."
Write-Host ""
Write-Host "Endpoint только читает SQLite. Денег/акций/бизнесов/сезона не меняет."
Write-Host "Но тест МОЖЕТ временно замедлить production для реальных игроков."
Write-Host ""

if (-not (Get-Command k6 -ErrorAction SilentlyContinue)) {
    Write-Host "k6 не найден. Выполни: winget install k6 --source winget"
    exit 1
}

$token = Read-Host "Вставь LOAD_TEST_TOKEN из Railway Variables"
if (-not $token) {
    Write-Host "Token is empty. Cancelled."
    exit 1
}

$confirm = Read-Host "Для запуска на PRODUCTION напиши ATTACK"
if ($confirm -ne "ATTACK") {
    Write-Host "Отменено."
    exit 1
}

$env:BASE_URL = $BaseUrl
$env:LOAD_TEST_TOKEN = $token

New-Item -ItemType Directory -Force -Path ".\results_v4" | Out-Null

Write-Host ""
Write-Host "Запуск. Открой Railway -> corporation-game -> Metrics."
Write-Host "Не закрывай PowerShell до финального summary."
Write-Host ""

& k6 run `
    --summary-export ".\results_v4\game_read_summary.json" `
    ".\production_game_read_v4.js" 2>&1 |
    Tee-Object -FilePath ".\results_v4\game_read_console.txt"

$exit = $LASTEXITCODE

Write-Host ""
Write-Host "============================================"
Write-Host "TEST FINISHED. k6 exit code: $exit"
Write-Host "============================================"
Write-Host ""
Write-Host "Пришли ChatGPT:"
Write-Host "  results_v4\game_read_summary.json"
Write-Host "  results_v4\game_read_console.txt"
Write-Host "  + скрин Railway Metrics"
Write-Host ""
