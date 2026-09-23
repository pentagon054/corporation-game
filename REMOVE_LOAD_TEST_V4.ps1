param(
    [string]$ProjectPath = "C:\Users\Pentagon\Desktop\corporation_game_MA"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

python (Join-Path $here "remove_load_test_v4.py") $ProjectPath

Write-Host ""
Write-Host "Теперь отправь удаление endpoint в GitHub:"
Write-Host "cd `"$ProjectPath`""
Write-Host "git add app.py"
Write-Host 'git commit -m "Remove temporary load test endpoint v4"'
Write-Host "git push"
Write-Host ""
Write-Host "После успешного Railway deploy удали LOAD_TEST_TOKEN из Variables."
