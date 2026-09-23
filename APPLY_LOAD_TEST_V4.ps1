param(
    [string]$ProjectPath = "C:\Users\Pentagon\Desktop\corporation_game_MA"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

python (Join-Path $here "apply_load_test_v4.py") $ProjectPath

Write-Host ""
Write-Host "Теперь отправь временный endpoint в GitHub:"
Write-Host "cd `"$ProjectPath`""
Write-Host "git add app.py"
Write-Host 'git commit -m "Add temporary read-only load test endpoint v4"'
Write-Host "git push"
