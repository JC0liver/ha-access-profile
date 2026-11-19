# Restart ap-testbed WITH the access_profile UI mounts, check it loads, take screenshots.
# Run after the UI agent has written ..\ui\custom_components\access_profile and ..\ui\data.
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$uiComp = Join-Path $PSScriptRoot '..\ui\custom_components\access_profile'
$uiData = Join-Path $PSScriptRoot '..\ui\data'
if (-not (Test-Path -LiteralPath (Join-Path $uiComp 'manifest.json'))) { throw "Missing $uiComp\manifest.json" }
if (-not (Test-Path -LiteralPath (Join-Path $uiData 'profiles.json'))) { Write-Warning "Missing $uiData\profiles.json (integration may show no data)" }
if (-not (Test-Path -LiteralPath '.secrets.env')) { throw 'No .secrets.env: run start.ps1 then .venv\Scripts\python.exe -I onboard.py first' }

# Recreate the container with the full compose.yaml (adds the two read-only mounts) and wait.
& (Join-Path $PSScriptRoot 'start.ps1') -Recreate

Write-Host "`n--- mounts ---"
docker inspect ap-testbed --format '{{range .Mounts}}{{.Destination}} rw={{.RW}}{{println}}{{end}}'

Write-Host "--- log lines mentioning access_profile ---"
docker logs ap-testbed 2>&1 | Select-String -SimpleMatch 'access_profile'
Write-Host "--- ERROR/CRITICAL/Traceback lines ---"
docker logs ap-testbed 2>&1 | Select-String -Pattern 'ERROR|CRITICAL|Traceback'

Write-Host "`n--- API check and screenshots ---"
& (Join-Path $PSScriptRoot '.venv\Scripts\python.exe') -I (Join-Path $PSScriptRoot 'check_ui.py') @args
exit $LASTEXITCODE
