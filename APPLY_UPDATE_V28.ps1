param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'
$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'app.py')) -or !(Test-Path -LiteralPath (Join-Path $ProjectPath 'web/premium_v25.js'))) {
    throw 'Select the existing Corporation project (v26.3), containing app.py and web/premium_v25.js.'
}
$files = @(
    'app.py', 'web/app.js', 'web/index.html', 'web/v20.js',
    'web/premium_v24.js', 'web/premium_v25.js',
    'web/instances_v28.js', 'web/instances_v28.css',
    'tests/test_instances_v28.py', 'tests/test_instances_v28.cjs',
    'README_V28_RU.md'
)
foreach ($relative in $files) {
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) { throw "Missing update file: $relative" }
}
$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v28_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($relative in $files) {
    $destination = Join-Path $ProjectPath $relative
    if (Test-Path -LiteralPath $destination) {
        $backupFile = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupFile -Parent) | Out-Null
        Copy-Item -LiteralPath $destination -Destination $backupFile
    }
}
foreach ($relative in $files) {
    $destination = Join-Path $ProjectPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $destination -Force
}
Write-Host "Update applied to: $ProjectPath"
Write-Host "Previous source files: $backup"
Write-Host 'bot.py, .env, databases and Railway configuration were preserved.'
Write-Host 'Review git diff, then commit and push the updated files.'
