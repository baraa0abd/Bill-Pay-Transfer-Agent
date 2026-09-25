param([ValidateSet('seed','test','eval','run')][string]$Target = 'test')
$pythonPath = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = 'python' }
switch ($Target) {
    seed { & $pythonPath -m data.seed }
    test { & $pythonPath -m pytest -q }
    eval { & $pythonPath -m eval.run_eval }
    run { & $pythonPath -m uvicorn app:app --host 127.0.0.1 --port 8000 }
}
exit $LASTEXITCODE

