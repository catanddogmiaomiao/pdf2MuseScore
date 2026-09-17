[CmdletBinding()]
param([switch]$GuiOnly, [string]$RuntimePython = "")

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath $PSScriptRoot).Path
Set-Location -LiteralPath $projectRoot

if (-not $GuiOnly) {
    & "$projectRoot\build-portable.ps1" -RuntimePython $RuntimePython
    exit $LASTEXITCODE
}

Write-Host 'Building PDF2Muse for Windows...'
python -c "import PyInstaller, PyQt6" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw 'Build dependencies are missing. Run: python -m pip install -r requirements-build.txt'
}

python -m PyInstaller --noconfirm --clean PDF2Muse.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$executable = Join-Path $projectRoot 'dist\PDF2Muse\PDF2Muse.exe'
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) {
    throw "Build finished without the expected executable: $executable"
}

Write-Host "Build complete: $executable"
