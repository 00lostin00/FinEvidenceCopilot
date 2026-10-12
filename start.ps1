param([int]$Port = 8012)
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not $env:FINEVIDENCE_PROVIDER) { $env:FINEVIDENCE_PROVIDER = 'offline' }
    uv run --frozen --all-extras uvicorn finevidence.api:app --host 127.0.0.1 --port $Port
} finally { Pop-Location }
