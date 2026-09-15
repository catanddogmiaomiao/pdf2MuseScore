param(
    [Parameter(Mandatory = $true)][string]$Pdf,
    [Parameter(Mandatory = $true)][string]$Audiveris,
    [string]$OutputRoot = (Join-Path $PSScriptRoot '../output')
)

$ErrorActionPreference = 'Stop'
$inputFile = (Resolve-Path -LiteralPath $Pdf).Path
$executable = (Resolve-Path -LiteralPath $Audiveris).Path
if ([IO.Path]::GetExtension($inputFile) -ine '.pdf') { throw 'Input must be a PDF.' }
if ([IO.Path]::GetExtension($executable) -ine '.exe') { throw 'Use the official Windows console Audiveris.exe.' }
$runId = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$runDirectory = [IO.Path]::GetFullPath((Join-Path $OutputRoot $runId))
New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
$versionLog = Join-Path $runDirectory 'version.log'
$consoleLog = Join-Path $runDirectory 'console.log'
$arguments = @('-batch', '-transcribe', '-export', '-save', '-output', $runDirectory, '--', $inputFile)
$record = [ordered]@{
    started_at = (Get-Date).ToString('o')
    input = $inputFile
    input_sha256 = (Get-FileHash -LiteralPath $inputFile -Algorithm SHA256).Hash
    executable = $executable
    arguments = $arguments
    version_exit_code = $null
    conversion_exit_code = $null
    elapsed_seconds = $null
    outputs = @()
    status = 'starting'
}
$timer = [Diagnostics.Stopwatch]::StartNew()
try {
    # Native stderr can contain normal Java messages. Save it alongside stdout.
    $ErrorActionPreference = 'Continue'
    & $executable -version > $versionLog 2>&1
    $record.version_exit_code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    if ($record.version_exit_code -ne 0) { throw "Audiveris failed to start. See $versionLog" }
    Write-Host "Recognizing PDF. Log: $consoleLog"
    $timer.Restart()
    $ErrorActionPreference = 'Continue'
    & $executable @arguments > $consoleLog 2>&1
    $record.conversion_exit_code = $LASTEXITCODE
    $ErrorActionPreference = 'Stop'
    $timer.Stop()
    $record.elapsed_seconds = [math]::Round($timer.Elapsed.TotalSeconds, 3)
    $record.outputs = @(Get-ChildItem -LiteralPath $runDirectory -Recurse -File |
        Where-Object { $_.Extension -in @('.mxl', '.musicxml') } |
        Select-Object -ExpandProperty FullName)
    if ($record.conversion_exit_code -ne 0) { throw 'Audiveris reported failure; any exported files require review.' }
    if ($record.outputs.Count -eq 0) { throw 'Audiveris exited without an MXL/MusicXML output. Inspect the log.' }
    $record.status = 'exported_needs_manual_review'
    Write-Host 'Export completed. Recognition accuracy still requires manual review.'
    $record.outputs | ForEach-Object { Write-Host $_ }
}
catch {
    $record.status = 'failed'
    $record.error = $_.Exception.Message
    Write-Host $record.error -ForegroundColor Red
}
finally {
    $record | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $runDirectory 'run.json') -Encoding UTF8
    Write-Host "Run record: $runDirectory"
}
if ($record.status -eq 'failed') { exit 1 }

