param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'
$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'app.py'))) { throw 'app.py was not found. Select the Corporation project folder.' }

$files = @(
  'app.py',
  'web/index.html',
  'web/app.js',
  'web/subscription_gate_v32.js',
  'web/referrals_v33.js',
  'web/referrals_v33.css',
  'web/corporation_dialogs_v33.js',
  'web/corporation_dialogs_v33.css',
  'web/v29.js',
  'web/v22_admin.js',
  'web/admin.html',
  'tests/test_v33_4_frontend.py'
)
foreach ($relative in $files) {
  if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) { throw "Update file missing: $relative" }
}
$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v33_4_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($relative in $files) {
  $current = Join-Path $ProjectPath $relative
  if (Test-Path -LiteralPath $current) {
    $dest = Join-Path $backup $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
    Copy-Item -LiteralPath $current -Destination $dest -Force
  }
}
foreach ($relative in $files) {
  $dest = Join-Path $ProjectPath $relative
  New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $dest -Force
}

# Verify critical fixes actually landed.
$index = Get-Content -LiteralPath (Join-Path $ProjectPath 'web/index.html') -Raw
$gate = Get-Content -LiteralPath (Join-Path $ProjectPath 'web/subscription_gate_v32.js') -Raw
$dialogs = Get-Content -LiteralPath (Join-Path $ProjectPath 'web/corporation_dialogs_v33.js') -Raw
if ($index -notmatch 'refGlobalEntry33' -or $index -notmatch 'refDesktopEntry33') { throw 'Referral entry verification failed.' }
if ($index -notmatch 'subscription_gate_v32\.js\?v=334') { throw 'Frontend cache-bust verification failed.' }
if ($gate -notmatch 'v29\.js\?v=334' -or $gate -notmatch 'referrals_v33\.js\?v=334') { throw 'Game script cache-bust verification failed.' }
if ($dialogs -notmatch 'corpConfirm' -or $dialogs -notmatch 'corpPrompt' -or $dialogs -notmatch 'corpAlert') { throw 'Corporation dialog verification failed.' }

Write-Host ''
Write-Host 'Corporation v33.4 desktop referrals + all-dialog hotfix installed successfully.' -ForegroundColor Green
Write-Host "Project folder: $ProjectPath"
Write-Host "Backup folder: $backup"
Write-Host 'Cache generation: 334. Deploy both Railway services if your bot/backend are separate.'
