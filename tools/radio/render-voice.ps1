param([Parameter(Mandatory=$true)][string]$EpisodePath,[Parameter(Mandatory=$true)][string]$OutputDir)
$ErrorActionPreference = 'Stop'
$episode = Get-Content -LiteralPath $EpisodePath -Raw -Encoding UTF8 | ConvertFrom-Json
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
$speech = New-Object -ComObject SAPI.SpVoice
$token = New-Object -ComObject SAPI.SpObjectToken
$token.SetId('HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_JA-JP_HARUKA_11.0', '', $false)
$speech.Voice = $token
$speech.Rate = 0
$parts = [System.Collections.Generic.List[object]]::new()
$parts.Add([PSCustomObject]@{kind='opening';index=$null;lines=@($episode.opening)})
for ($i=0; $i -lt $episode.news.Count; $i++) { $parts.Add([PSCustomObject]@{kind='news';index=$i;lines=@($episode.news[$i].lines)}) }
$parts.Add([PSCustomObject]@{kind='closing';index=$null;lines=@($episode.closing)})
$rendered = [System.Collections.Generic.List[object]]::new()
$lineIndex=0
for ($partIndex=0; $partIndex -lt $parts.Count; $partIndex++) {
  foreach ($line in $parts[$partIndex].lines) {
    if ([string]::IsNullOrWhiteSpace($line.say) -or [string]::IsNullOrWhiteSpace($line.show)) { throw 'A spoken line is empty' }
    $filename = '{0:D3}.wav' -f $lineIndex
    $outputPath = Join-Path $OutputDir $filename
    $stream = New-Object -ComObject SAPI.SpFileStream
    try {
      $stream.Format.Type = 22
      $stream.Open($outputPath,3,$false)
      $speech.AudioOutputStream=$stream
      [void]$speech.Speak([string]$line.say,16)
    } finally { $stream.Close() }
    $rendered.Add([PSCustomObject]@{file=$filename;part=$partIndex;kind=$parts[$partIndex].kind;index=$parts[$partIndex].index;show=$line.show})
    $lineIndex++
  }
}
@{voice='Microsoft Haruka Desktop - Japanese';lines=@($rendered)} | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $OutputDir 'rendered.json') -Encoding utf8
Write-Output ('Rendered {0} lines with Microsoft Haruka Desktop' -f $lineIndex)
