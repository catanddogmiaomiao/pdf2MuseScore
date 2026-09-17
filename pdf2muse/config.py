from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings


class AppConfig:
    def __init__(self) -> None:
        self._settings = QSettings()

    @property
    def language(self) -> str:
        value = self._settings.value("ui/language", "zh_CN", str)
        return value if value in ("zh_CN", "en", "ja", "ko") else "zh_CN"

    @language.setter
    def language(self, value: str) -> None:
        self._settings.setValue("ui/language", value)

    @property
    def homr_python(self) -> Path | None:
        value = self._settings.value("tools/homr_python", "", str)
        return Path(value) if value else None

    @homr_python.setter
    def homr_python(self, value: Path | None) -> None:
        self._settings.setValue("tools/homr_python", str(value or ""))

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
