# Demo launcher: fresh database every run, LLM-generated wallet, demo faults on, model from .env.
#   ./run-local.ps1                  # generated wallet (data/heldout_seed.json)
#   ./run-local.ps1 -DevelopmentSeed # development wallet (data/seed.json)
param([switch]$DevelopmentSeed)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# The provider comes from the shell or .env (rule parser if neither sets it); this script never overrides it.
if (-not $env:LLM_PROVIDER -and (Test-Path .env)) {
    $line = Select-String -Path .env -Pattern '^\s*LLM_PROVIDER\s*=\s*(\S+)' | Select-Object -First 1
    if ($line) { $env:LLM_PROVIDER = $line.Matches[0].Groups[1].Value }
}
if (-not $env:LLM_PROVIDER) { $env:LLM_PROVIDER = 'rule' }
if ($env:LLM_PROVIDER -eq 'ollama') {
    if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = 'qwen3.5:4b' }
    $base = if ($env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL } else { 'http://127.0.0.1:11434' }
    $tags = Invoke-RestMethod ($base.TrimEnd('/') + '/api/tags')
    if ($env:OLLAMA_MODEL -notin $tags.models.name) { throw "Run: ollama pull $env:OLLAMA_MODEL" }
}

$env:DEMO_MODE = 'true'
$env:SEED_PATH = if ($DevelopmentSeed) { 'data/seed.json' } else { 'data/heldout_seed.json' }
if (-not (Test-Path -LiteralPath $env:SEED_PATH)) { throw "Missing $env:SEED_PATH. Generate it: python -m data.generate_mock_data seed" }
# New database per run, so a rehearsal never reuses a spent demo wallet.
$env:DATABASE_URL = 'sqlite:///demo-' + [guid]::NewGuid().ToString('N') + '.db'

$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = 'python' }
& $pythonPath -m data.seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Parser: $env:LLM_PROVIDER | Wallet: $env:SEED_PATH | Database: $env:DATABASE_URL | http://127.0.0.1:8000"
& $pythonPath -m uvicorn app:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
