param([string]$InputFile, [string]$OutputFile, [switch]$List)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($List) {
        $voices = @($speaker.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object {
            @{ name = $_.VoiceInfo.Name; culture = $_.VoiceInfo.Culture.Name }
        })
        ConvertTo-Json -InputObject $voices -Compress
    } else {
        $request = Get-Content -LiteralPath $InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $voice = $speaker.GetInstalledVoices() | Where-Object { $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'zh-TW' } | Select-Object -First 1
        if (-not $voice) { throw 'No installed zh-TW desktop voice. Install a Traditional Chinese Windows voice.' }
        $speaker.SelectVoice($voice.VoiceInfo.Name)
        $speaker.Rate = [int]$request.rate
        $speaker.SetOutputToWaveFile($OutputFile)
        $speaker.Speak([string]$request.text)
        $speaker.SetOutputToNull()
    }
} finally { $speaker.Dispose() }
