[CmdletBinding()]
param([string]$RuntimePython = "", [switch]$SkipBuild)
$ErrorActionPreference = 'Stop'
$portableProject = (Resolve-Path -LiteralPath $PSScriptRoot).Path
Set-Location -LiteralPath $portableProject
if (-not $RuntimePython) {
    $RuntimePython = Join-Path $portableProject '.homr-runtime\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $RuntimePython)) {
        $RuntimePython = Join-Path $env:LOCALAPPDATA 'PDF2Muse\homr-runtime\Scripts\python.exe'
    }
}
if (-not (Test-Path -LiteralPath $RuntimePython -PathType Leaf)) { throw 'Create the build environment with setup-homr.ps1 first.' }
& $RuntimePython -c 'import homr, PyInstaller; print("HOMR build environment ready")'
if ($LASTEXITCODE -ne 0) { throw 'Install requirements-engine-build.txt into the HOMR build environment first.' }
if (-not $SkipBuild) {
    & "$portableProject\build.ps1" -GuiOnly
    if ($LASTEXITCODE -ne 0) { throw 'GUI packaging failed' }
    & $RuntimePython -m PyInstaller --noconfirm HOMR.spec
    if ($LASTEXITCODE -ne 0) { throw 'HOMR packaging failed' }
}
$portableTarget = Join-Path $portableProject 'dist\PDF2Muse'
if (-not (Test-Path -LiteralPath (Join-Path $portableTarget 'PDF2Muse.exe'))) { throw 'GUI executable missing' }
if (-not (Test-Path -LiteralPath (Join-Path $portableTarget 'engine\HOMR.exe'))) {
    if (-not (Test-Path -LiteralPath (Join-Path $portableProject 'dist\HOMR\HOMR.exe'))) { throw 'Engine executable missing' }
    Copy-Item -LiteralPath (Join-Path $portableProject 'dist\HOMR') -Destination (Join-Path $portableTarget 'engine') -Recurse
}
& (Join-Path $portableTarget 'engine\HOMR.exe') --self-test
if ($LASTEXITCODE -ne 0) { throw 'Bundled engine self-test failed' }
# Binary downloads carry notices, while complete corresponding source is offered separately.
Copy-Item -LiteralPath (Join-Path $portableProject 'THIRD-PARTY-NOTICES.md') -Destination $portableTarget -Force
Copy-Item -LiteralPath (Join-Path $portableProject 'LICENSE') -Destination $portableTarget -Force
Copy-Item -LiteralPath (Join-Path $portableProject 'SOURCE-DEPENDENCIES.json') -Destination $portableTarget -Force
$portableZip = Join-Path $portableProject 'dist\PDF2Muse-Windows-x64-portable.zip'
python (Join-Path $portableProject 'packaging\make_zip.py') $portableTarget $portableZip
if ($LASTEXITCODE -ne 0) { throw 'Portable ZIP creation or integrity verification failed' }
Write-Host "Portable package complete: $portableZip"
