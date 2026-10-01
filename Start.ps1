$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw 'Missing Python environment. Follow README.md setup instructions.' }
try {
    $existing = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 3
    if ($existing.model -eq 'gemma3:4b') { Start-Process 'http://127.0.0.1:8765'; exit 0 }
} catch {}
try { $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/tags' -TimeoutSec 3 }
catch {
    $ollamaCommand = (Get-Command ollama.exe -ErrorAction Stop).Source
    Start-Process -FilePath $ollamaCommand -ArgumentList 'serve' -WindowStyle Hidden
    Start-Sleep -Seconds 2
}
$runtime = Join-Path $PSScriptRoot '.runtime'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
$process = Start-Process -FilePath $python -ArgumentList '-m','uvicorn','app:app','--host','127.0.0.1','--port','8765' -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtime 'server.log') -RedirectStandardError (Join-Path $runtime 'server-error.log') -PassThru
@{ pid=$process.Id; startTicks=$process.StartTime.ToUniversalTime().Ticks } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtime 'server-process.json') -Encoding UTF8
for ($attempt=0; $attempt -lt 20; $attempt++) {
    Start-Sleep -Milliseconds 500
    try { $null = Invoke-RestMethod 'http://127.0.0.1:8765/api/health' -TimeoutSec 2; Start-Process 'http://127.0.0.1:8765'; exit 0 } catch {}
}
throw 'Server did not start. See .runtime/server-error.log.'
