param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'app.py')) -or !(Test-Path -LiteralPath (Join-Path $ProjectPath 'web/instances_v28.js'))) {
    throw 'Select the current Corporation v28 project folder. It must contain app.py and web/instances_v28.js.'
}

$files = @(
    'app.py',
    'web/index.html',
    'web/v29.js',
    'web/v29.css',
    'tests/test_v29.py',
    'README_V29_RU.md'
)

foreach ($relative in $files) {
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) {
        throw "Update file is missing from archive: $relative"
    }
}

$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v29_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
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
Write-Host 'Corporation v29 installed successfully.' -ForegroundColor Green
Write-Host "Project folder: $ProjectPath"
Write-Host "Backup folder: $backup"
Write-Host 'bot.py, .env, database files, and Railway settings were not changed.'
Write-Host 'Review git diff, then commit and push.'
