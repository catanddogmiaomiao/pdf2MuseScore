[CmdletBinding()]
param(
    [string]$EngineDir,
    [string]$InnoCompiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe',
    [string]$OutputDir = '',
    [switch]$SkipGuiBuild
)
$ErrorActionPreference = 'Stop'
$releaseProject = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$releasePayload = Join-Path $releaseProject 'dist\PDF2Muse'
if (-not $OutputDir) { $OutputDir = Join-Path $releaseProject 'dist' }
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
if (-not $SkipGuiBuild) {
    & (Join-Path $releaseProject 'build.ps1') -GuiOnly
    if ($LASTEXITCODE -ne 0) { throw 'GUI build failed' }
}
if ($EngineDir) {
    $releaseEngineSource = (Resolve-Path -LiteralPath $EngineDir).Path
    if (-not (Test-Path -LiteralPath (Join-Path $releaseEngineSource 'HOMR.exe'))) { throw 'Engine executable missing' }
    if (Test-Path -LiteralPath (Join-Path $releasePayload 'engine')) { throw 'Engine target already exists. Use a fresh GUI build.' }
    Copy-Item -LiteralPath $releaseEngineSource -Destination (Join-Path $releasePayload 'engine') -Recurse
}
if (-not (Test-Path -LiteralPath (Join-Path $releasePayload 'engine\HOMR.exe'))) { throw 'A complete frozen HOMR engine is required' }
& (Join-Path $releasePayload 'engine\HOMR.exe') --self-test
if ($LASTEXITCODE -ne 0) { throw 'Engine or model integrity self-test failed' }
Copy-Item -LiteralPath (Join-Path $releaseProject 'THIRD-PARTY-NOTICES.md') -Destination $releasePayload -Force
Copy-Item -LiteralPath (Join-Path $releaseProject 'LICENSE') -Destination $releasePayload -Force
Copy-Item -LiteralPath (Join-Path $releaseProject 'SOURCE-DEPENDENCIES.json') -Destination $releasePayload -Force
Copy-Item -LiteralPath (Join-Path $releaseProject 'legal') -Destination (Join-Path $releasePayload '_internal') -Recurse -Force
if (-not (Test-Path -LiteralPath $InnoCompiler)) { throw 'Install Inno Setup 6 or newer and pass -InnoCompiler.' }
& $InnoCompiler "/DPayloadDir=$releasePayload" "/DInstallerOutput=$OutputDir" (Join-Path $PSScriptRoot 'installer.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
Write-Host (Join-Path $OutputDir 'PDF2Muse-0.3.0-Windows-x64-Setup.exe')
