$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
$env:UV_CACHE_DIR = Join-Path (Get-Location).Path '.runtime/uv-cache'
if (-not (Test-Path -LiteralPath '.venv-local-tts/Scripts/python.exe')) {
    uv venv --python 3.11 .venv-local-tts
    if ($LASTEXITCODE -ne 0) { throw 'Could not create optional Hakka environment.' }
}
uv pip install --python .venv-local-tts/Scripts/python.exe --index-url https://download.pytorch.org/whl/cpu torch==2.6.0 torchaudio==2.6.0
if ($LASTEXITCODE -ne 0) { throw 'Could not install CPU PyTorch.' }
uv pip install --python .venv-local-tts/Scripts/python.exe coqui-tts==0.27.5 transformers==4.57.6 formog2p==0.1.3
if ($LASTEXITCODE -ne 0) { throw 'Could not install Hakka dependencies.' }
& .venv/Scripts/python.exe -X utf8 scripts/download_hakka.py
if ($LASTEXITCODE -ne 0) { throw 'Could not download verified Hakka model files.' }
Write-Output 'Hakka ready. Restart Paper Voice and open the Hakka panel.'
