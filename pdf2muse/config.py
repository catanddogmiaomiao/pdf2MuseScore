from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings


class AppConfig:
    def __init__(self) -> None:
        self._settings = QSettings()

    @property
    def audiveris_path(self) -> Path | None:
        value = self._settings.value("tools/audiveris", "", str)
        return Path(value) if value else None

    @audiveris_path.setter
    def audiveris_path(self, value: Path | None) -> None:
        self._settings.setValue("tools/audiveris", str(value or ""))

    @property
    def musescore_path(self) -> Path | None:
        value = self._settings.value("tools/musescore", "", str)
        return Path(value) if value else None

    @musescore_path.setter
    def musescore_path(self, value: Path | None) -> None:
        self._settings.setValue("tools/musescore", str(value or ""))

    @property
    def output_dir(self) -> Path | None:
        value = self._settings.value("conversion/output_dir", "", str)
        return Path(value) if value else None

    @output_dir.setter
    def output_dir(self, value: Path | None) -> None:
        self._settings.setValue("conversion/output_dir", str(value or ""))
