$ErrorActionPreference = 'Stop'
$recordPath = Join-Path $PSScriptRoot '.runtime\server-process.json'
if (-not (Test-Path -LiteralPath $recordPath)) { Write-Output 'No launcher-owned server record.'; exit 0 }
$record = Get-Content -LiteralPath $recordPath -Raw -Encoding UTF8 | ConvertFrom-Json
$process = Get-Process -Id $record.pid -ErrorAction SilentlyContinue
if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $record.startTicks -and $process.Path -eq (Join-Path $PSScriptRoot '.venv\Scripts\python.exe')) {
    Stop-Process -Id $process.Id
    Write-Output 'Paper Voice stopped.'
} else { Write-Output 'Recorded process is no longer running; no process was stopped.' }
