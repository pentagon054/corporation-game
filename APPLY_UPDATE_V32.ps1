param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$appPath = Join-Path $ProjectPath 'app.py'
$v31Path = Join-Path $ProjectPath 'web/v31.js'
if (!(Test-Path -LiteralPath $appPath) -or !(Test-Path -LiteralPath $v31Path)) {
    throw 'Select the current Corporation v31 project folder. app.py and web/v31.js are required.'
}

$payloadFiles = @(
    'web/index.html',
    'web/subscription_gate_v32.js',
    'web/subscription_gate_v32.css',
    'README_V32_RU.md'
)

foreach ($relative in $payloadFiles) {
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) {
        throw "Update file is missing from archive: $relative"
    }
}
if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'apply_subscription_gate_v32.py'))) {
    throw 'apply_subscription_gate_v32.py is missing from archive.'
}

$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v32_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null

$backupFiles = @('app.py') + $payloadFiles
foreach ($relative in $backupFiles) {
    $source = Join-Path $ProjectPath $relative
    if (Test-Path -LiteralPath $source) {
        $destination = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

foreach ($relative in $payloadFiles) {
    $destination = Join-Path $ProjectPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $destination -Force
}

$patcher = Join-Path $PSScriptRoot 'apply_subscription_gate_v32.py'
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
if ($pyLauncher) {
    & py -3 $patcher --project $ProjectPath
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (!$python) { throw 'Python was not found in PATH.' }
    & python $patcher --project $ProjectPath
}
if ($LASTEXITCODE -ne 0) { throw 'Backend patch failed.' }

Write-Host ''
Write-Host 'Corporation v32 installed successfully.' -ForegroundColor Green
Write-Host "Project folder: $ProjectPath"
Write-Host "Backup folder: $backup"
Write-Host 'Required Railway variable: REQUIRED_CHANNEL=@Corpgame054'
Write-Host 'BOT_TOKEN stays server-side only.'
Write-Host 'Review git diff, then commit and push.'
