[CmdletBinding()]
param([string]$Root = "$env:USERPROFILE\JEFEAGUILA")

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$Dirs = @(
    'config',
    'docs',
    'evidence\01_ORIGINALS_READ_ONLY',
    'evidence\02_WORKING_COPIES',
    'evidence\03_REPORTS',
    'logs',
    'tools'
)
foreach ($Dir in $Dirs) {
    New-Item -ItemType Directory -Path (Join-Path $Root $Dir) -Force | Out-Null
}

$ConfigPath = Join-Path $Root 'config\installation.json'
if (Test-Path -LiteralPath $ConfigPath) {
    $BackupPath = "$ConfigPath.before_$(Get-Date -Format 'yyyyMMdd_HHmmss').backup"
    Copy-Item -LiteralPath $ConfigPath -Destination $BackupPath
    Write-Host "Previous configuration preserved: $BackupPath" -ForegroundColor Yellow
}

$State = [ordered]@{
    name = 'JEFEAGUILA'
    installed_utc = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')
    root = $Root
    platform = 'Windows'
    evidence_policy = 'preserve_originals'
}
$TemporaryPath = "$ConfigPath.tmp"
$State | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $TemporaryPath -Encoding UTF8
Get-Content -LiteralPath $TemporaryPath -Raw | ConvertFrom-Json | Out-Null
Move-Item -LiteralPath $TemporaryPath -Destination $ConfigPath -Force

Write-Host "JEFEAGUILA installed at $Root" -ForegroundColor Green
Write-Host 'No firewall, registry, startup, or security policy was changed.'
