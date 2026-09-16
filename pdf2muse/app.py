from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPalette
from PyQt6.QtWidgets import QApplication

from .ui import MainWindow


def resource_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "assets" / name


def dark_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#131315"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#F4F1EA"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#141416"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#19191C"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#242428"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#F4F1EA"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#F4F1EA"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#202024"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#F4F1EA"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#C8AFE0"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#171419"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#77747C"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#77747C"))
    return palette


def run() -> int:
    if sys.platform == "win32":
        os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    QCoreApplication.setOrganizationName("PDF2Muse")
    QCoreApplication.setApplicationName("PDF2Muse")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(dark_palette())
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
