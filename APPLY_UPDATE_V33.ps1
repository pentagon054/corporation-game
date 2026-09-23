param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'app.py'))) {
    throw 'app.py was not found. Select the Corporation project folder.'
}
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'web/subscription_gate_v32.js'))) {
    throw 'Corporation v32 subscription gate was not found. Install this update on the current v32.x project.'
}

$files = @(
    'app.py',
    'bot.py',
    'web/index.html',
    'web/subscription_gate_v32.js',
    'web/app.js',
    'web/v20.js',
    'web/v29.js',
    'web/audit_v23.js',
    'web/v22_admin.js',
    'web/admin.html',
    'web/corporation_dialogs_v33.js',
    'web/corporation_dialogs_v33.css',
    'web/referrals_v33.js',
    'web/referrals_v33.css',
    'tests/test_referrals_v33.py',
    'README_V33_RU.md'
)

foreach ($relative in $files) {
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) {
        throw "Update file is missing from archive: $relative"
    }
}

$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v33_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null

foreach ($relative in $files) {
    $current = Join-Path $ProjectPath $relative
    if (Test-Path -LiteralPath $current) {
        $backupFile = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupFile -Parent) | Out-Null
        Copy-Item -LiteralPath $current -Destination $backupFile -Force
    }
}

# Local database is never overwritten. If it exists, keep a safety copy too.
$dbFile = Join-Path $ProjectPath 'corporation.db'
if (Test-Path -LiteralPath $dbFile) {
    Copy-Item -LiteralPath $dbFile -Destination (Join-Path $backup 'corporation.db') -Force
}

foreach ($relative in $files) {
    $destination = Join-Path $ProjectPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $destination -Force
}

Write-Host ''
Write-Host 'Corporation v33 prerelease update installed successfully.' -ForegroundColor Green
Write-Host "Project folder: $ProjectPath"
Write-Host "Backup folder: $backup"
Write-Host 'Player database and Railway settings were not overwritten.'
Write-Host 'Run the validation commands from README_V33_RU.md, review git diff, then commit and push.'
