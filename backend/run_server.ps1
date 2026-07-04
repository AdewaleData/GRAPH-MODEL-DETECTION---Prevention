# Start Halal Graph DDoS API
$root = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$root\src;$PSScriptRoot"
Set-Location $PSScriptRoot
Write-Host "Starting API at http://127.0.0.1:8000/docs"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
