from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _valid(path: Path | None) -> Path | None:
    return path.resolve() if path and path.is_file() else None


def find_homr_python(configured: Path | None = None) -> Path | None:
    import sys
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
    local = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'PDF2Muse'
    for candidate in (base / 'engine' / 'HOMR.exe', configured, base / '.homr-runtime' / 'Scripts' / 'python.exe',
                      local / 'homr-runtime' / 'Scripts' / 'python.exe'):
        if found := _valid(candidate):
            return found
    return None


def find_musescore(configured: Path | None = None) -> Path | None:
    candidates = [configured]
    for command in ("MuseScore4.exe", "MuseScore.exe", "mscore.exe"):
        if found := shutil.which(command):
            candidates.append(Path(found))
    candidates.extend(
        [
            Path(r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"),
            Path(r"C:\Program Files\MuseScore Studio 4\bin\MuseScore4.exe"),
            Path(r"C:\Program Files\MuseScore Studio\bin\MuseScore4.exe"),
            Path(r"C:\Program Files (x86)\MuseScore 4\bin\MuseScore4.exe"),
        ]
    )
    program_files = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
    candidates.extend(program_files.glob("MuseScore*/*/MuseScore4.exe"))
    for candidate in candidates:
        if found := _valid(candidate):
            return found
    return None


def open_in_musescore(executable: Path, score: Path) -> None:
    subprocess.Popen([str(executable), str(score)], close_fds=True)


def open_output_folder(folder: Path) -> None:
    """Check availability and let Explorer open the folder; propagate OS errors."""
    folder = folder.resolve(strict=True)
    if not folder.is_dir():
        raise NotADirectoryError(str(folder))
    os.startfile(str(folder), "explore")
