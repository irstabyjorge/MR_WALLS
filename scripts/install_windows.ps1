[CmdletBinding()]
param([string]$Root = "$env:USERPROFILE\JEFEAGUILA")
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Dirs = @('config','docs','evidence\01_ORIGINALS_READ_ONLY','evidence\02_WORKING_COPIES','evidence\03_REPORTS','logs','tools')
foreach ($Dir in $Dirs) { New-Item -ItemType Directory -Path (Join-Path $Root $Dir) -Force | Out-Null }
$State = [ordered]@{name='JEFEAGUILA';installed_utc=[DateTime]::UtcNow.ToString('o');root=$Root;platform='Windows';evidence_policy='preserve_originals'}
$State | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Root 'config\installation.json') -Encoding UTF8
Write-Host "JEFEAGUILA installed at $Root" -ForegroundColor Green
Write-Host 'No firewall, registry, startup, or security policy was changed.'
