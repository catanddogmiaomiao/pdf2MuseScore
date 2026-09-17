param([string]$Python = "python", [string]$Runtime = "$env:LOCALAPPDATA\PDF2Muse\homr-runtime")
$ErrorActionPreference = "Stop"
& $Python -c "import sys; assert sys.version_info[:2] in ((3,11),(3,12)), 'Use Python 3.11 or 3.12'"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 or 3.12 is required" }
& $Python -m venv $Runtime
if ($LASTEXITCODE -ne 0) { throw "Unable to create HOMR environment" }
$HomrPython = Join-Path $Runtime "Scripts\python.exe"
$env:POETRY_DYNAMIC_VERSIONING_BYPASS = "0.7.0+5e51b434"
& $HomrPython -m pip install -r "$PSScriptRoot\requirements-homr.txt"
if ($LASTEXITCODE -ne 0) { throw "HOMR installation failed" }
& $HomrPython -u -m homr.main --init
if ($LASTEXITCODE -ne 0) { throw "HOMR model initialization failed" }
& $HomrPython -m pip freeze | Set-Content (Join-Path $Runtime "installed-versions.txt")
Write-Host "HOMR ready: $HomrPython"
