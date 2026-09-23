param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'app.py'))) {
    throw 'app.py was not found. Select the Corporation project folder.'
}
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'web/index.html'))) {
    throw 'web/index.html was not found. Select the Corporation project folder.'
}

$files = @(
    'app.py',
    'web/index.html',
    'web/app.js',
    'web/referrals_v33.js',
    'web/referrals_v33.css',
    'web/admin.html',
    'web/v22_admin.js',
    'web/corporation_dialogs_v33.css',
    'web/corporation_dialogs_v33.js',
    'README_V33_RU.md'
)

foreach ($relative in $files) {
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) {
        throw "Update file is missing from archive: $relative"
    }
}

$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v33_2_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null

foreach ($relative in $files) {
    $current = Join-Path $ProjectPath $relative
    if (Test-Path -LiteralPath $current) {
        $backupFile = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupFile -Parent) | Out-Null
        Copy-Item -LiteralPath $current -Destination $backupFile -Force
    }
}

foreach ($relative in $files) {
    $destination = Join-Path $ProjectPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $destination -Force
}

Write-Host ''
Write-Host 'Corporation v33.2 mobile/admin hotfix installed successfully.' -ForegroundColor Green
Write-Host "Project folder: $ProjectPath"
Write-Host "Backup folder: $backup"
Write-Host 'Now restart/deploy the backend and clear Telegram Mini App cache by reopening the bot.'
