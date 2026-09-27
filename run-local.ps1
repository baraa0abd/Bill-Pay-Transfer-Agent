param([switch]$DevelopmentSeed)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:LLM_PROVIDER = 'ollama'
if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = 'qwen3.5:4b' }
if (-not $env:OLLAMA_BASE_URL) { $env:OLLAMA_BASE_URL = 'http://127.0.0.1:11434' }
$env:DEMO_MODE = 'true'
$env:SEED_PATH = if ($DevelopmentSeed) { 'data/seed.json' } else { 'data/heldout_seed.json' }
if (-not (Test-Path -LiteralPath $env:SEED_PATH)) {
    throw 'Generate the held-out wallet first: set LLM_PROVIDER=ollama and run python -m data.generate_mock_data seed. Use -DevelopmentSeed only for an explicitly development-fixture demo.'
}
$tags = Invoke-RestMethod ($env:OLLAMA_BASE_URL.TrimEnd('/') + '/api/tags')
if ($env:OLLAMA_MODEL -notin $tags.models.name) { throw "Run ollama pull $env:OLLAMA_MODEL first." }
# New database per rehearsal; never silently reuse a spent demo wallet.
$env:DATABASE_URL = 'sqlite:///demo-' + [guid]::NewGuid().ToString('N') + '.db'
$pythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = 'python' }
& $pythonPath -m data.seed
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Local model: $env:OLLAMA_MODEL | Seed: $env:SEED_PATH | Database: $env:DATABASE_URL"
& $pythonPath -m uvicorn app:app --host 127.0.0.1 --port 8000
exit $LASTEXITCODE
