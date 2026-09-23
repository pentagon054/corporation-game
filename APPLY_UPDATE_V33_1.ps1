param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'app.py'))) {
    throw 'app.py was not found. Select the Corporation project folder.'
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
    'web/referrals_v33.css',
    'web/referrals_v33_1.js',
    'tests/test_referrals_v33.py',
    'tests/test_v33_1_visibility.cjs',
    'README_V33_1_RU.md',
    'VERSION_V33_1.txt'
)

foreach ($relative in $files) {
    $source = Join-Path $PSScriptRoot $relative
    if (!(Test-Path -LiteralPath $source)) {
        throw "Update file is missing from archive: $relative"
    }
}

$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v33_1_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null

foreach ($relative in $files) {
    $current = Join-Path $ProjectPath $relative
    if (Test-Path -LiteralPath $current) {
        $backupFile = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $backupFile -Parent) | Out-Null
        Copy-Item -LiteralPath $current -Destination $backupFile -Force
    }
}

$dbFile = Join-Path $ProjectPath 'corporation.db'
if (Test-Path -LiteralPath $dbFile) {
    Copy-Item -LiteralPath $dbFile -Destination (Join-Path $backup 'corporation.db') -Force
}

foreach ($relative in $files) {
    $destination = Join-Path $ProjectPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $destination -Force
}

# Remove the old referral loader so only v33.1 is used. The file may remain in git history,
# but index/subscription loader now references referrals_v33_1.js?v=331.
$oldReferral = Join-Path $ProjectPath 'web/referrals_v33.js'
if (Test-Path -LiteralPath $oldReferral) {
    Copy-Item -LiteralPath $oldReferral -Destination (Join-Path $backup 'web/referrals_v33.js') -Force
    Remove-Item -LiteralPath $oldReferral -Force
}

# Verify the update really landed in the target folder.
$appText = Get-Content -LiteralPath (Join-Path $ProjectPath 'app.py') -Raw
$gateText = Get-Content -LiteralPath (Join-Path $ProjectPath 'web/subscription_gate_v32.js') -Raw
$refText = Get-Content -LiteralPath (Join-Path $ProjectPath 'web/referrals_v33_1.js') -Raw
$botText = Get-Content -LiteralPath (Join-Path $ProjectPath 'bot.py') -Raw

if ($appText -notmatch 'CORPORATION_REFERRALS_V33_BEGIN') { throw 'Verification failed: referral backend marker is missing from app.py' }
if ($gateText -notmatch 'referrals_v33_1\.js\?v=331') { throw 'Verification failed: v33.1 referral loader is not connected' }
if ($refText -notmatch 'ref-entry-main331') { throw 'Verification failed: visible main-page referral card is missing' }
if ($refText -notmatch 'refTopButton331') { throw 'Verification failed: header referral button is missing' }
if ($botText -notmatch 'WEBAPP_VERSION = "331"') { throw 'Verification failed: bot cache version was not bumped to 331' }

Write-Host ''
Write-Host 'Corporation v33.1 installed and verified.' -ForegroundColor Green
Write-Host "Project folder: $ProjectPath"
Write-Host "Backup folder: $backup"
Write-Host 'Visible changes: gift button in the header, referral card on Main, referral card in Rating.' -ForegroundColor Cyan
Write-Host 'Database was preserved. Commit and push the changed files, then redeploy BOTH web/backend and bot services if they are separate.' -ForegroundColor Yellow
