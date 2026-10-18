param([ValidateSet('seed','test','eval','heldout','review','run')][string]$Target = 'test')
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = 'python' }
switch ($Target) {
    seed { & $pythonPath -m data.seed }
    test { & $pythonPath -m pytest -q }  # temp dir comes from pyproject.toml
    eval { & $pythonPath -m eval.run_eval }
    heldout { & $pythonPath -m eval.run_eval --heldout }
    review { & $pythonPath -m data.review_web }  # held-out review page, http://127.0.0.1:8010
    run { & $pythonPath -m uvicorn app:app --host 127.0.0.1 --port 8000 }
}
exit $LASTEXITCODE

