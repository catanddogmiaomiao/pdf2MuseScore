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
    Move-Item -LiteralPath (Join-Path $portableProject 'dist\HOMR') -Destination (Join-Path $portableTarget 'engine')
}
& (Join-Path $portableTarget 'engine\HOMR.exe') --self-test
if ($LASTEXITCODE -ne 0) { throw 'Bundled engine self-test failed' }
# Include the corresponding source, build scripts and license notices.
$portableSource = Join-Path $portableTarget 'source'
New-Item -ItemType Directory -Path $portableSource -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $portableProject 'pdf2muse') -Destination $portableSource -Recurse -Force
Copy-Item -LiteralPath (Join-Path $portableProject 'assets') -Destination $portableSource -Recurse -Force
Copy-Item -LiteralPath (Join-Path $portableProject 'packaging') -Destination $portableSource -Recurse -Force
Copy-Item -LiteralPath (Join-Path $portableProject 'docs') -Destination $portableSource -Recurse -Force
Copy-Item -LiteralPath (Join-Path $portableProject 'tests') -Destination $portableSource -Recurse -Force
foreach ($portableFile in @('main.py', 'HOMR.spec', 'PDF2Muse.spec', 'requirements.txt', 'requirements-homr.txt', 'requirements-build.txt', 'requirements-engine-build.txt', 'setup-homr.ps1', 'build.ps1', 'build-portable.ps1', 'README.md', 'THIRD-PARTY-NOTICES.md')) {
    Copy-Item -LiteralPath (Join-Path $portableProject $portableFile) -Destination $portableSource
}
$homrSource = & $RuntimePython -c 'import homr,pathlib; print(pathlib.Path(homr.__file__).parent)'
foreach ($homrFile in Get-ChildItem -LiteralPath $homrSource -Recurse -File) {
    if ($homrFile.Extension -in @('.py', '.json')) {
        $homrRelative = $homrFile.FullName.Substring($homrSource.Length).TrimStart('\')
        $homrDestination = Join-Path (Join-Path $portableSource 'homr') $homrRelative
        New-Item -ItemType Directory -Path (Split-Path -Parent $homrDestination) -Force | Out-Null
        Copy-Item -LiteralPath $homrFile.FullName -Destination $homrDestination
    }
}
Copy-Item -LiteralPath (Join-Path $portableProject 'THIRD-PARTY-NOTICES.md') -Destination $portableTarget
$portableZip = Join-Path $portableProject 'dist\PDF2Muse-Windows-x64-portable.zip'
python (Join-Path $portableProject 'packaging\make_zip.py') $portableTarget $portableZip
if ($LASTEXITCODE -ne 0) { throw 'Portable ZIP creation or integrity verification failed' }
Write-Host "Portable package complete: $portableZip"
