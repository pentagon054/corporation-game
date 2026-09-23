param([Parameter(Mandatory=$true)][string]$ProjectPath)
$ErrorActionPreference = 'Stop'

$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
$webPath = Join-Path $ProjectPath 'web'
$required = @(
    'web/index.html',
    'web/subscription_gate_v32.js',
    'web/subscription_gate_v32.css'
)

if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'app.py'))) {
    throw 'app.py was not found. Select the Corporation project folder.'
}
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'web/v31.js'))) {
    throw 'web/v31.js was not found. Install this hotfix on Corporation v31/v32.'
}
if (!(Test-Path -LiteralPath (Join-Path $ProjectPath 'web/subscription_gate_v32.js'))) {
    throw 'Corporation v32 subscription gate was not found. Install v32 first.'
}

foreach ($relative in $required) {
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot $relative))) {
        throw "Update file is missing from archive: $relative"
    }
}

$backup = Join-Path (Split-Path $ProjectPath -Parent) ((Split-Path $ProjectPath -Leaf) + '_before_v32_4_' + (Get-Date -Format 'yyyyMMdd_HHmmss_fff'))
New-Item -ItemType Directory -Path $backup | Out-Null

foreach ($relative in $required) {
    $source = Join-Path $ProjectPath $relative
    if (Test-Path -LiteralPath $source) {
        $destination = Join-Path $backup $relative
        New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
}

foreach ($relative in $required) {
    $destination = Join-Path $ProjectPath $relative
    New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $relative) -Destination $destination -Force
}

$readmeSource = Join-Path $PSScriptRoot 'README_V32_4_RU.md'
if (Test-Path -LiteralPath $readmeSource) {
    Copy-Item -LiteralPath $readmeSource -Destination (Join-Path $ProjectPath 'README_V32_4_RU.md') -Force
}

Write-Host ''
Write-Host 'Corporation v32.4 hotfix installed successfully.' -ForegroundColor Green
Write-Host "Project folder: $ProjectPath"
Write-Host "Backup folder: $backup"
Write-Host 'Backend subscription protection was not changed.'
Write-Host 'The 3D Corporation coin startup screen is installed.'
