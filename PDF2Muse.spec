# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import importlib.metadata


project_root = Path(SPECPATH).resolve()
assets_dir = project_root / "assets"
qt_licenses = []
for name in ('PyQt6', 'PyQt6-Qt6', 'PyQt6-sip'):
    distribution = importlib.metadata.distribution(name)
    for file in distribution.files or []:
        if any(part.lower().startswith(('license', 'copying', 'notice')) for part in file.parts):
            path = Path(distribution.locate_file(file))
            if path.is_file():
                qt_licenses.append((str(path), str(Path('licenses') / name / Path(file).parent)))

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "pdf2muse" / "homr_runner.py"), "pdf2muse"),
        (str(project_root / "setup-homr.ps1"), "."),
        (str(project_root / "requirements-homr.txt"), "."),
        (str(assets_dir / "app-icon.png"), "assets"),
        (str(assets_dir / "app-icon.ico"), "assets"),
    ] + qt_licenses,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PySide2", "PySide6", "tkinter", "homr", "onnxruntime", "numpy", "cv2", "torch"],
    noarchive=False,
    optimize=1,
)

# Qt uses Windows ICU APIs. Poppler may introduce an incompatible ICU DLL.
import pefile
qt_core = next((entry[1] for entry in a.binaries if entry[0].lower().endswith('qt6core.dll')), None)
if qt_core:
    pe = pefile.PE(qt_core, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT']])
    windows_icu = any(
        item.dll.lower() == b'icu.dll' or
        (item.dll.lower() == b'icuuc.dll' and any(symbol.name == b'ucnv_open' for symbol in item.imports))
        for item in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])
    )
    pe.close()
    if windows_icu:
        a.binaries = [entry for entry in a.binaries if not Path(entry[0]).name.lower().startswith(('icuuc', 'icudt'))]
        a.datas = [entry for entry in a.datas if not Path(entry[0]).name.lower().startswith(('icuuc', 'icudt'))]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PDF2Muse",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=str(assets_dir / "app-icon.ico"),
    version=str(project_root / "packaging" / "version_info.txt"),
    uac_admin=False,
    uac_uiaccess=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PDF2Muse",
)
