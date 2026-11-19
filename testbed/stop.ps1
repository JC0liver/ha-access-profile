# Stop the ap-testbed container (keeps config/ so state survives).
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
docker compose -f compose.yaml -f compose.noui.yaml stop
