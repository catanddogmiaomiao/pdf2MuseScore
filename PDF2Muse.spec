# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import os
import pefile
from PyQt6.QtCore import QLibraryInfo


project_root = Path(SPECPATH).resolve()
assets_dir = project_root / "assets"

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(assets_dir / "app-icon.png"), "assets"),
        (str(assets_dir / "app-icon.ico"), "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PySide2", "PySide6", "tkinter"],
    noarchive=False,
    optimize=1,
)

# Qt 6.11 uses the Windows ICU API (unversioned ucnv_open). A developer PATH
# may contain Poppler/Conda ICU with versioned symbols such as ucnv_open_78.
# Let Windows load its platform ICU instead of bundling that incompatible DLL.
qt_bin = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.BinariesPath))
qt_core = pefile.PE(str(qt_bin / "Qt6Core.dll"))
uses_windows_icu = any(
    entry.dll.lower() == b"icuuc.dll" and any(symbol.name == b"ucnv_open" for symbol in entry.imports)
    for entry in qt_core.DIRECTORY_ENTRY_IMPORT
)
if uses_windows_icu and (Path(os.environ["SystemRoot"]) / "System32" / "icuuc.dll").exists():
    a.binaries = [entry for entry in a.binaries
                  if Path(entry[0]).name.lower() != "icuuc.dll"
                  and not (Path(entry[0]).name.lower().startswith("icudt")
                           and Path(entry[1]).parent != qt_bin)]

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
