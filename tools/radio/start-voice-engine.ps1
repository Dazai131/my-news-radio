param([string]$EnginePath = (Join-Path $PSScriptRoot 'software/runtime/COEIROINK_WIN_CPU_v.2.13.0/engine/engine.exe'))
$ErrorActionPreference = 'Stop'
$voiceApi = 'http://127.0.0.1:50032/v1/speakers'
function Test-RadioVoice {
  try {
    $speakers = Invoke-RestMethod -Uri $voiceApi -TimeoutSec 3
    return @($speakers | Where-Object { $_.speakerName -eq 'リリンちゃん' -and @($_.styles | Where-Object { $_.styleId -eq 90 }).Count -eq 1 }).Count -eq 1
  } catch { return $false }
}
if (Test-RadioVoice) { Write-Output 'COEIROINK: Lilin normal is ready'; exit 0 }
if (Get-NetTCPConnection -State Listen -LocalPort 50032 -ErrorAction SilentlyContinue) {
  throw 'The local voice engine is running but Lilin normal is unavailable. Do not use a different voice.'
}
if (-not (Test-Path -LiteralPath $EnginePath)) { throw 'COEIROINK engine is missing. Restore the approved local installation.' }
$voiceEngine = (Resolve-Path -LiteralPath $EnginePath).Path
$voiceLog = Join-Path $PSScriptRoot ('engine-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
Start-Process -FilePath $voiceEngine -WorkingDirectory (Split-Path -Parent $voiceEngine) -WindowStyle Hidden -RedirectStandardOutput ($voiceLog + '-stdout.log') -RedirectStandardError ($voiceLog + '-stderr.log') | Out-Null
for ($attempt = 0; $attempt -lt 30; $attempt++) {
  if (Test-RadioVoice) { Write-Output 'COEIROINK: Lilin normal is ready'; exit 0 }
  Start-Sleep -Seconds 1
}
throw 'COEIROINK did not become ready. Keep the existing episode and report the voice error.'
