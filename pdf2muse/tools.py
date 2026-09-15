from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _valid(path: Path | None) -> Path | None:
    return path.resolve() if path and path.is_file() else None


def find_audiveris(configured: Path | None = None) -> Path | None:
    candidates = [
        configured,
        Path(os.environ.get("AUDIVERIS_PATH", "")) if os.environ.get("AUDIVERIS_PATH") else None,
        Path(r"C:\Program Files\Audiveris\Audiveris.exe"),
        Path(r"C:\Program Files\Audiveris\bin\Audiveris.exe"),
        Path(r"C:\Program Files (x86)\Audiveris\Audiveris.exe"),
    ]
    on_path = shutil.which("Audiveris") or shutil.which("Audiveris.exe")
    if on_path:
        candidates.insert(1, Path(on_path))
    for candidate in candidates:
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
