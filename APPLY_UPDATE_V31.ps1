param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'app.py')) -or !(Test-Path -LiteralPath (Join-Path $ProjectPath 'web/v29.js'))) {
    throw 'Select the current Corporation v29 project folder. It must contain app.py and web/v29.js.'
}

$files = @(
    'web/index.html',
    'web/interactive_map.js',
    'web/premium_v24.js',
    'web/gestures_v30.js',
    'web/gestures_v30.css',
    'web/v31.js',
    'web/v31.css',
    'tests/test_v31.cjs',
    'README_V31_RU.md'
)

foreach ($relative in $files) {
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) {
        throw "Update file is missing from archive: $relative"
    }
}

$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v31_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null

foreach ($relative in $files) {
    $destination = Join-Path $ProjectPath $relative
    if (Test-Path -LiteralPath $destination) {
        $backupFile = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupFile -Parent) | Out-Null
        Copy-Item -LiteralPath $destination -Destination $backupFile -Force
    }
}

foreach ($relative in $files) {
    $destination = Join-Path $ProjectPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $destination -Force
}

Write-Host ''
Write-Host 'Corporation v31 installed successfully.' -ForegroundColor Green
Write-Host "Project folder: $ProjectPath"
Write-Host "Backup folder: $backup"
Write-Host 'app.py, bot.py, .env, database files, and Railway settings were not changed.'
Write-Host 'Review git diff, then commit and push.'
