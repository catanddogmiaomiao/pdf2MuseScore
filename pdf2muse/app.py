from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QFont, QFontDatabase, QIcon
from PyQt6.QtWidgets import QApplication

from .ui import MainWindow


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / name


def run() -> int:
    if sys.platform == "win32":
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    QCoreApplication.setOrganizationName("PDF2Muse")
    QCoreApplication.setApplicationName("PDF2Muse")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    windows_font = Path(r"C:\Windows\Fonts\msyh.ttc")
    if windows_font.exists():
        QFontDatabase.addApplicationFont(str(windows_font))
    app.setFont(QFont("Microsoft YaHei UI", 10))
    icon = resource_path("app-icon.png")
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))

    window = MainWindow()
    window.show()
    return app.exec()
