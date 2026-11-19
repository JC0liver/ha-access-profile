# Start the ap-testbed Home Assistant container and wait until it answers.
# -Recreate forces a fresh container (a full restart that picks up integration code changes).
param([switch]$Recreate)
$ErrorActionPreference = 'Stop'
$extra = @()
if ($Recreate) { $extra = @('--force-recreate') }
Set-Location -LiteralPath $PSScriptRoot

$uiComp = Join-Path $PSScriptRoot '..\ui\custom_components\access_profile'
$uiData = Join-Path $PSScriptRoot '..\ui\data'
New-Item -ItemType Directory -Force (Join-Path $PSScriptRoot 'config') | Out-Null

if ((Test-Path -LiteralPath $uiComp) -and (Test-Path -LiteralPath $uiData)) {
    Write-Host 'UI integration found: starting with access_profile mounts.'
    docker compose -f compose.yaml up -d @extra
} else {
    Write-Warning 'UI folders missing (..\ui\custom_components\access_profile and/or ..\ui\data). Starting WITHOUT the UI mounts.'
    docker compose -f compose.yaml -f compose.noui.yaml up -d @extra
}
if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed' }

Write-Host 'Waiting for http://127.0.0.1:8124 ...'
$deadline = (Get-Date).AddMinutes(5)
while ((Get-Date) -lt $deadline) {
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8124/manifest.json' -UseBasicParsing -TimeoutSec 5
        if ($r.StatusCode -eq 200) { Write-Host 'Home Assistant is up: http://127.0.0.1:8124'; exit 0 }
    } catch { }
    Start-Sleep -Seconds 3
}
throw 'Home Assistant did not come up within 5 minutes. See: docker logs ap-testbed'
