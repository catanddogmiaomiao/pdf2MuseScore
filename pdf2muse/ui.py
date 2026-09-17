from __future__ import annotations

from pathlib import Path
import threading

from PyQt6.QtCore import QPointF, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QLayout,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .config import AppConfig
from .library import ScoreLibrary
from .library_ui import LibraryPage
from .i18n import tr, set_language, retranslate, LANGUAGES
from .converter import ConversionError, ConversionResult, ConversionCancelled, MemoryConversionError, convert_with_homr
from .tools import find_homr_python, find_musescore, open_in_musescore, open_output_folder


C = {
    "window": "#131315", "card": "#19191C", "input": "#141416",
    "border": "#35353B", "text": "#F4F1EA", "muted": "#98979F",
    "accent": "#C8AFE0", "hover": "#D4BCE9", "danger": "#E39A9A",
}

STYLE = f"""
QWidget {{ color:{C['text']}; font-family:'Microsoft YaHei UI'; font-size:14px; }}
QMainWindow, QWidget#root {{ background:{C['window']}; }}
QDialog, QMessageBox {{ background:{C['card']}; }}
QMessageBox QLabel {{ color:{C['text']}; background:transparent; }}
QMessageBox QLabel#qt_msgbox_label {{ min-width:340px; }}
QMessageBox QPushButton {{ background:#242428; color:{C['text']}; min-width:88px; }}
QMessageBox QPushButton:hover {{ background:#2D2D32; border-color:#5A5962; }}
QFrame#card {{ background:{C['card']}; border:1px solid {C['border']}; border-radius:14px; }}
QLabel#section {{ font-size:20px; font-weight:600; }}
QLabel#brand {{ font-size:29px; font-weight:600; }}
QLabel#subtitle, QLabel#muted {{ color:{C['muted']}; }}
QLabel#dropTitle {{ font-size:21px; font-weight:600; }}
QPushButton {{ background:transparent; border:1px solid {C['border']}; border-radius:10px; padding:0 18px; min-height:42px; }}
QPushButton:hover {{ border-color:#5A5962; background:#202024; }}
QPushButton#primary {{ background:{C['accent']}; color:#171419; border:0; font-size:16px; font-weight:600; min-height:52px; }}
QPushButton#primary:hover {{ background:{C['hover']}; }}
QPushButton#primary:disabled {{ background:#4A414F; color:#8C818F; }}
QPushButton#light {{ background:{C['text']}; color:#171719; border:0; font-weight:600; min-height:46px; }}
QPushButton#link {{ border:0; padding:0; min-height:32px; }}
QPushButton#link:hover {{ color:{C['accent']}; background:transparent; }}
QLineEdit, QComboBox {{ background:{C['input']}; border:1px solid {C['border']}; border-radius:10px; padding:0 15px; min-height:48px; }}
QLineEdit:focus, QComboBox:focus {{ border-color:{C['accent']}; }}
QComboBox::drop-down {{ border:0; width:36px; }}
QComboBox QAbstractItemView {{ background:#202024; border:1px solid {C['border']}; selection-background-color:#3E3545; }}
QProgressBar {{ background:#2B2B30; border:0; border-radius:4px; height:8px; text-align:center; color:transparent; }}
QProgressBar::chunk {{ background:{C['accent']}; border-radius:4px; }}
QPlainTextEdit {{ background:#111113; border:1px solid {C['border']}; border-radius:10px; padding:10px; color:#C9C7CE; font-family:Consolas; font-size:12px; }}
QPdfView {{ background:#111113; border:0; }}
"""


class DocumentGlyph(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setFixedSize(104, 124)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(C["text"]), 4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(18, 10, 70, 100, 10, 10)
        painter.drawLine(62, 10, 88, 36)
        painter.drawLine(62, 10, 62, 36)
        painter.drawLine(62, 36, 88, 36)
        for y, width in ((61, 49), (79, 49), (97, 30)):
            painter.drawLine(30, y, 30 + width, y)


class DropZone(QFrame):
    fileDropped = pyqtSignal(Path)

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("dropZone")
        self.setStyleSheet(
            f"QFrame#dropZone{{background:#151517;border:1px dashed #55545D;border-radius:12px;}}"
            f"QFrame#dropZone[active='true']{{border:2px solid {C['accent']};background:#1D1A21;}}"
        )
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(10)
        layout.addWidget(DocumentGlyph(), 0, Qt.AlignmentFlag.AlignHCenter)
        title = QLabel(tr("拖放 PDF 乐谱"))
        title.setObjectName("dropTitle")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignHCenter)
        subtitle = QLabel(tr("或从电脑中选择文件"))
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(15)
        self.choose_button = QPushButton(tr("＋    选择 PDF"))
        self.choose_button.setObjectName("light")
        self.choose_button.setFixedWidth(182)
        layout.addWidget(self.choose_button, 0, Qt.AlignmentFlag.AlignHCenter)

    def _accepts(self, event) -> bool:
        urls = event.mimeData().urls()
        return len(urls) == 1 and urls[0].isLocalFile() and urls[0].toLocalFile().lower().endswith(".pdf")

    def _restyle(self, active: bool) -> None:
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event) -> None:
        if self._accepts(event):
            event.acceptProposedAction()
            self._restyle(True)

    def dragLeaveEvent(self, event) -> None:
        self._restyle(False)

    def dropEvent(self, event) -> None:
        self._restyle(False)
        if self._accepts(event):
            self.fileDropped.emit(Path(event.mimeData().urls()[0].toLocalFile()))
            event.acceptProposedAction()


class PdfPreview(QFrame):
    fileDropped = pyqtSignal(Path)
    chooseRequested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setAcceptDrops(True)
        self.setObjectName("pdfPreview")
        self.setStyleSheet(
            f"QFrame#pdfPreview{{background:#111113;border:1px solid {C['border']};border-radius:12px;}}"
            f"QFrame#pdfPreview[active='true']{{border:2px solid {C['accent']};}}"
        )
        self.document = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setDocument(self.document)
        self.view.setPageMode(QPdfView.PageMode.SinglePage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.view, 1)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.previous_button = QPushButton(tr("上一页"))
        self.previous_button.setFixedHeight(34)
        self.next_button = QPushButton(tr("下一页"))
        self.next_button.setFixedHeight(34)
        self.page_label = QLabel(tr("第 0 / 0 页"))
        self.page_label.setObjectName("muted")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        change_button = QPushButton(tr("更换 PDF"))
        change_button.setFixedHeight(34)
        self.previous_button.clicked.connect(lambda: self._jump(-1))
        self.next_button.clicked.connect(lambda: self._jump(1))
        change_button.clicked.connect(self.chooseRequested)
        toolbar.addWidget(self.previous_button)
        toolbar.addWidget(self.next_button)
        toolbar.addStretch()
        toolbar.addWidget(self.page_label)
        toolbar.addStretch()
        toolbar.addWidget(change_button)
        layout.addLayout(toolbar)

        self.document.pageCountChanged.connect(self._update_navigation)
        self.view.pageNavigator().currentPageChanged.connect(self._update_navigation)
        self._update_navigation()

    @property
    def page_count(self) -> int:
        return self.document.pageCount()

    def load_pdf(self, path: Path) -> bool:
        self.document.close()
        error = self.document.load(str(path))
        if error != QPdfDocument.Error.None_:
            return False
        self.view.pageNavigator().jump(0, QPointF(0, 0), 0)
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)
        self._update_navigation()
        return True

    def clear(self) -> None:
        self.document.close()
        self._update_navigation()

    def _jump(self, offset: int) -> None:
        count = self.document.pageCount()
        if count <= 0:
            return
        current = self.view.pageNavigator().currentPage()
        page = max(0, min(count - 1, current + offset))
        self.view.pageNavigator().jump(page, QPointF(0, 0), 0)
        self.view.setZoomMode(QPdfView.ZoomMode.FitInView)

    def _update_navigation(self, *args) -> None:
        count = self.document.pageCount()
        current = self.view.pageNavigator().currentPage() if count else -1
        self.page_label.setText(tr("第 {page} / {count} 页", page=current + 1 if count else 0, count=count))
        self.previous_button.setEnabled(count > 0 and current > 0)
        self.next_button.setEnabled(count > 0 and current < count - 1)

    def _accepts(self, event) -> bool:
        urls = event.mimeData().urls()
        return len(urls) == 1 and urls[0].isLocalFile() and urls[0].toLocalFile().lower().endswith(".pdf")

    def _restyle(self, active: bool) -> None:
        self.setProperty("active", active)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event) -> None:
        if self._accepts(event):
            event.acceptProposedAction()
            self._restyle(True)

    def dragLeaveEvent(self, event) -> None:
        self._restyle(False)

    def dropEvent(self, event) -> None:
        self._restyle(False)
        if self._accepts(event):
            self.fileDropped.emit(Path(event.mimeData().urls()[0].toLocalFile()))
            event.acceptProposedAction()


class ConversionWorker(QThread):
    stage = pyqtSignal(str)
    cancelled = pyqtSignal()
    log = pyqtSignal(str)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(object)

    def __init__(self, pdf: Path, output_dir: Path, homr_python: Path) -> None:
        super().__init__()
        self.pdf, self.output_dir, self.homr_python = pdf, output_dir, homr_python
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            result = convert_with_homr(
                self.pdf, self.output_dir, self.homr_python,
                self.log.emit, self.stage.emit, self.cancel_event,
            )
        except ConversionCancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(exc)
        else:
            self.succeeded.emit(result)


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle(tr("设置"))
        self.setMinimumWidth(620)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)
        heading = QLabel(tr("本地工具路径"))
        heading.setObjectName("section")
        layout.addWidget(heading)
        note = QLabel(tr("首次使用请运行 setup-homr.ps1，下载依赖和模型。"))
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addWidget(QLabel(tr("语言")))
        self.language_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.language_combo.addItem(name, code)
        self.language_combo.setCurrentIndex(self.language_combo.findData(config.language))
        layout.addWidget(self.language_combo)
        layout.addSpacing(8)
        self.homr_edit = self._path_row(layout, tr("HOMR 独立环境 Python"), config.homr_python, "python.exe")
        self.musescore_edit = self._path_row(layout, "MuseScore Studio", config.musescore_path, "MuseScore4.exe")
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton(tr("取消"))
        save = QPushButton(tr("保存"))
        save.setObjectName("primary")
        save.setFixedWidth(110)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addSpacing(10)
        layout.addLayout(buttons)

    def _path_row(self, layout: QVBoxLayout, title: str, value: Path | None, executable: str) -> QLineEdit:
        layout.addWidget(QLabel(title))
        row = QHBoxLayout()
        edit = QLineEdit(str(value or ""))
        edit.setPlaceholderText(tr("自动检测"))
        browse = QPushButton(tr("浏览…"))
        browse.clicked.connect(lambda: self._browse(edit, executable))
        row.addWidget(edit, 1)
        row.addWidget(browse)
        layout.addLayout(row)
        return edit

    def _browse(self, edit: QLineEdit, executable: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("选择程序"), edit.text(), tr("{executable} (*.exe);;程序 (*.exe)", executable=executable))
        if path:
            edit.setText(path)

    def _save(self) -> None:
        self.config.homr_python = Path(self.homr_edit.text()) if self.homr_edit.text() else None
        self.config.musescore_path = Path(self.musescore_edit.text()) if self.musescore_edit.text() else None
        self.config.language = self.language_combo.currentData()
        set_language(self.config.language)
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig()
        set_language(self.config.language)
        self.pdf_path: Path | None = None
        self.output_path: Path | None = None
        self.log_path: Path | None = None
        self.worker: ConversionWorker | None = None
        self._log_lines: list[str] = []
        self.library = ScoreLibrary()
        self.library_entry = None
        self.setWindowTitle("PDF2Muse")
        self.setMinimumSize(980, 780)
        self.resize(1200, 780)
        self.setStyleSheet(STYLE)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(34, 24, 34, 18)
        outer.setSpacing(20)
        outer.addLayout(self._header())
        self.pages = QStackedWidget()
        conversion_page = QWidget()
        content = QHBoxLayout(conversion_page)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(18)
        content.addWidget(self._import_card(), 1)
        content.addLayout(self._right_column(), 1)
        self.pages.addWidget(conversion_page)
        self.library_page = LibraryPage(self.library)
        self.library_page.importRequested.connect(self._choose_pdf)
        self.library_page.scoreRequested.connect(self._restore_score)
        self.library_page.openRequested.connect(self._open_score_file)
        self.library_page.folderRequested.connect(self._open_folder)
        self.library_page.removed.connect(self._library_removed)
        self.pages.addWidget(self.library_page)
        outer.addWidget(self.pages, 1)
        outer.addWidget(self._footer())
        self._refresh_controls()

    def _header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        icon = QLabel()
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setFixedSize(48, 48)
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "app-icon.png"
        if icon_path.exists():
            icon.setPixmap(QPixmap(str(icon_path)).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        titles = QVBoxLayout()
        titles.setSpacing(0)
        brand = QLabel("pdf2muse")
        brand.setObjectName("brand")
        subtitle = QLabel(tr("PDF 乐谱转换"))
        subtitle.setObjectName("subtitle")
        titles.addWidget(brand)
        titles.addWidget(subtitle)
        settings = QPushButton(tr("设置"))
        settings.clicked.connect(self._show_settings)
        row.addWidget(icon)
        row.addSpacing(8)
        row.addLayout(titles)
        row.addStretch()
        self.conversion_tab = QPushButton(tr('转换'))
        self.library_tab = QPushButton(tr('曲谱库'))
        for index, button in enumerate((self.conversion_tab, self.library_tab)):
            button.setCheckable(True)
            button.setStyleSheet("QPushButton:checked{background:#2B2532;color:#C8AFE0;border-color:#746080;}")
            button.clicked.connect(lambda checked, page=index: self._switch_page(page))
            row.addWidget(button)
        self.conversion_tab.setChecked(True)
        row.addWidget(settings)
        return row

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)
        return frame, layout

    def _import_card(self) -> QFrame:
        frame, layout = self._card()
        self.import_title = QLabel(tr("导入乐谱"))
        self.import_title.setObjectName("section")
        layout.addWidget(self.import_title)
        self.drop_zone = DropZone()
        self.drop_zone.setMinimumHeight(330)
        self.drop_zone.choose_button.clicked.connect(self._choose_pdf)
        self.drop_zone.fileDropped.connect(self._set_pdf)
        self.pdf_preview = PdfPreview()
        self.pdf_preview.chooseRequested.connect(self._choose_pdf)
        self.pdf_preview.fileDropped.connect(self._set_pdf)
        self.import_stack = QStackedWidget()
        self.import_stack.setStyleSheet("QStackedWidget{background:transparent;border:0;}")
        self.import_stack.addWidget(self.drop_zone)
        self.import_stack.addWidget(self.pdf_preview)
        self.import_stack.setCurrentWidget(self.drop_zone)
        layout.addWidget(self.import_stack, 1)
        self.file_panel = QFrame()
        self.file_panel.setObjectName("filePanel")
        self.file_panel.setStyleSheet(f"QFrame#filePanel{{background:#151517;border:1px solid {C['border']};border-radius:10px;}}")
        file_row = QHBoxLayout(self.file_panel)
        file_row.setContentsMargins(16, 12, 12, 12)
        badge = QLabel("PDF")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(42, 42)
        badge.setStyleSheet(f"background:#28222E;color:{C['accent']};border:1px solid #574A62;border-radius:8px;font-size:11px;font-weight:600;")
        file_text = QVBoxLayout()
        self.file_name = QLabel(tr("尚未选择文件"))
        self.file_meta = QLabel(tr("请选择一份 PDF 乐谱"))
        self.file_meta.setObjectName("muted")
        file_text.addWidget(self.file_name)
        file_text.addWidget(self.file_meta)
        clear = QPushButton("×")
        clear.setObjectName("link")
        clear.setFixedWidth(34)
        clear.setToolTip(tr("移除文件"))
        clear.clicked.connect(self._clear_pdf)
        file_row.addWidget(badge)
        file_row.addSpacing(5)
        file_row.addLayout(file_text, 1)
        file_row.addWidget(clear)
        layout.addWidget(self.file_panel)
        return frame

    def _right_column(self) -> QVBoxLayout:
        column = QVBoxLayout()
        column.setSpacing(18)
        settings, layout = self._card()
        title = QLabel(tr("转换设置"))
        title.setObjectName("section")
        layout.addWidget(title)
        layout.addWidget(QLabel(tr("输出格式")))
        self.format_combo = QComboBox()
        self.format_combo.addItem(tr("MusicXML 文件 (.musicxml)"), "musicxml")
        layout.addWidget(self.format_combo)
        layout.addWidget(QLabel(tr("保存位置")))
        path_row = QHBoxLayout()
        self.output_edit = QLineEdit(str(self.config.output_dir or ""))
        self.output_edit.setPlaceholderText(tr("与原文件相同的文件夹"))
        browse = QPushButton(tr("选择"))
        browse.setMinimumWidth(96)
        browse.setToolTip(tr("选择输出文件夹"))
        browse.clicked.connect(self._choose_output_dir)
        path_row.addWidget(self.output_edit, 1)
        path_row.addWidget(browse)
        layout.addLayout(path_row)
        self.convert_button = QPushButton(tr("开始识别"))
        self.convert_button.setObjectName("primary")
        self.convert_button.clicked.connect(self._toggle_conversion)
        layout.addWidget(self.convert_button)
        column.addWidget(settings)

        status, layout = self._card()
        title = QLabel(tr("识别状态"))
        title.setObjectName("section")
        layout.addWidget(title)
        self.status_label = QLabel(tr("●  等待开始"))
        self.status_label.setObjectName("muted")
        layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        layout.addWidget(self.progress)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color:{C['border']};")
        layout.addWidget(line)
        suspect_row = QHBoxLayout()
        suspect_row.addWidget(QLabel(tr("输出结果")))
        suspect_row.addStretch()
        self.suspect_summary = QLabel(tr("完成后可在 MuseScore 中试听"))
        self.suspect_summary.setObjectName("muted")
        suspect_row.addWidget(self.suspect_summary)
        layout.addLayout(suspect_row)
        self.result_label = QLabel("")
        self.result_label.setProperty("literalText", True)
        self.result_label.setWordWrap(True)
        self.result_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.result_label)
        self.folder_button = QPushButton(tr("打开输出文件夹"))
        self.folder_button.clicked.connect(self._open_output_folder)
        layout.addWidget(self.folder_button)
        action_row = QHBoxLayout()
        self.open_button = QPushButton(tr("在 MuseScore 中打开"))
        self.open_button.clicked.connect(self._open_result)
        log_button = QPushButton(tr("查看日志 →"))
        log_button.setObjectName("link")
        log_button.clicked.connect(self._show_log)
        action_row.addWidget(self.open_button, 1)
        action_row.addWidget(log_button)
        layout.addLayout(action_row)
        column.addWidget(status, 1)
        return column

    def _footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(32)
        row = QHBoxLayout(footer)
        row.setContentsMargins(4, 0, 4, 0)
        label = QLabel(tr("免费  ·  本地识别  ·  无需上传"))
        label.setObjectName("muted")
        row.addWidget(label)
        row.addStretch()
        version = QLabel("PDF2Muse 0.2 · HOMR")
        version.setObjectName("muted")
        row.addWidget(version)
        return footer

    def _choose_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("选择 PDF 乐谱"), "", tr("PDF 乐谱 (*.pdf)"))
        if path:
            self._set_pdf(Path(path))

    def _set_pdf(self, path: Path) -> None:
        if self.worker and self.worker.isRunning():
            return
        if path.suffix.lower() != ".pdf" or not path.is_file():
            QMessageBox.warning(self, tr("无法导入"), tr("请选择有效的 PDF 文件。"))
            return
        old_path = self.pdf_path
        if not self.pdf_preview.load_pdf(path):
            if old_path:
                self.pdf_preview.load_pdf(old_path)
            QMessageBox.warning(self, tr("无法预览"), tr("无法读取这份 PDF，文件可能损坏或受到密码保护。"))
            return
        try:
            entry = self.library.import_pdf(path, self.pdf_preview.page_count)
            owned_path = Path(entry['pdf'])
            if not self.pdf_preview.load_pdf(owned_path):
                raise OSError(tr('原谱暂时无法访问'))
        except Exception as exc:
            if old_path:
                self.pdf_preview.load_pdf(old_path)
            else:
                self.pdf_preview.clear()
            QMessageBox.warning(self, tr('无法保存曲谱库'), str(exc))
            return
        self.library_entry = entry
        path = owned_path
        self._switch_page(0)
        self.pdf_path = path.resolve()
        self.log_path = None
        self._log_lines.clear()
        self.result_label.clear()
        self.output_path = None
        self.import_title.setText(tr("乐谱预览"))
        self.import_stack.setCurrentWidget(self.pdf_preview)
        self.file_name.setText(path.name)
        self.file_name.setProperty("literalText", True)
        self.file_name.setToolTip(str(path))
        size_mb = path.stat().st_size / (1024 * 1024)
        self.file_meta.setText(tr("PDF 乐谱  ·  {pages} 页  ·  {size} MB  ·  已就绪", pages=self.pdf_preview.page_count, size=f"{size_mb:.1f}"))
        self.status_label.setText(tr("●  已选择文件"))
        self.status_label.setStyleSheet("")
        self.suspect_summary.setText(tr("完成后可在 MuseScore 中试听"))
        self.progress.setValue(0)
        self._refresh_controls()
        self.library_page.reload(entry['id'])

    def _clear_pdf(self) -> None:
        if self.worker and self.worker.isRunning():
            return
        self.log_path = None
        self._log_lines.clear()
        self.result_label.clear()
        self.pdf_path = self.output_path = None
        self.library_entry = None
        self.pdf_preview.clear()
        self.import_title.setText(tr("导入乐谱"))
        self.import_stack.setCurrentWidget(self.drop_zone)
        self.file_name.setText(tr("尚未选择文件"))
        self.file_name.setProperty("literalText", False)
        self.file_meta.setText(tr("请选择一份 PDF 乐谱"))
        self.status_label.setText(tr("●  等待开始"))
        self.status_label.setStyleSheet("")
        self.suspect_summary.setText(tr("完成后可在 MuseScore 中试听"))
        self.progress.setValue(0)
        self._refresh_controls()

    def _choose_output_dir(self) -> None:
        start = self.output_edit.text() or (str(self.pdf_path.parent) if self.pdf_path else "")
        path = QFileDialog.getExistingDirectory(self, tr("选择保存位置"), start)
        if path:
            self.output_edit.setText(path)
            self.config.output_dir = Path(path)

    def _show_settings(self) -> None:
        if SettingsDialog(self.config, self).exec() == QDialog.DialogCode.Accepted:
            retranslate(self)
            self.library_page.reload()
            self._refresh_controls()

    def _start_conversion(self) -> None:
        if not self.pdf_path or (self.worker and self.worker.isRunning()):
            return
        homr_python = find_homr_python(self.config.homr_python)
        if not homr_python:
            QMessageBox.warning(self, tr("尚未配置 HOMR"), tr("请先运行 setup-homr.ps1 安装本地识别环境，再在设置中选择该环境的 python.exe。"))
            self._show_settings()
            return
        output_dir = Path(self.output_edit.text()).expanduser() if self.output_edit.text().strip() else self.pdf_path.parent
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, tr("无法使用保存位置"), str(exc))
            return
        self.config.output_dir = output_dir if self.output_edit.text().strip() else None
        self.status_label.setStyleSheet("")
        self.status_label.setText(tr("●  正在识别乐谱…"))
        self.suspect_summary.setText(tr("正在分析页面和乐谱结构…"))
        self.progress.setRange(0, 0)
        self.log_path = None
        self.result_label.clear()
        self.output_path = None
        self._log_lines = []
        self.worker = ConversionWorker(self.pdf_path, output_dir, homr_python)
        self.worker.stage.connect(lambda text: self.status_label.setText("●  " + text))
        self.worker.cancelled.connect(self._conversion_cancelled)
        self.worker.log.connect(self._receive_log)
        self.worker.succeeded.connect(self._conversion_succeeded)
        self.worker.failed.connect(self._conversion_failed)
        self.worker.finished.connect(self._refresh_controls)
        self.worker.start()
        self._refresh_controls()

    def _toggle_conversion(self) -> None:
        if self.worker and self.worker.isRunning():
            self._cancel_conversion()
        else:
            self._start_conversion()

    def _receive_log(self, line: str) -> None:
        self._log_lines.append(line)
        self._log_lines = self._log_lines[-1000:]

    def _conversion_succeeded(self, result: ConversionResult) -> None:
        self.output_path, self.log_path = result.output, result.log_file
        if self.library_entry:
            try:
                self.library_entry = self.library.add_result(self.library_entry, result)
                self.library_page.reload(self.library_entry['id'])
            except Exception as exc:
                QMessageBox.warning(self, tr('无法保存曲谱库'), str(exc))
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.status_label.setStyleSheet(f"color:{C['accent']};")
        self.status_label.setText(tr("●  识别完成  ·  {seconds} 秒", seconds=f"{result.elapsed_seconds:.1f}"))
        self.suspect_summary.setText(tr("打开 MuseScore 试听并检查"))
        if result.skipped_pages:
            self.suspect_summary.setText(tr("已跳过纯空白页：{pages}", pages=", ".join(map(str, result.skipped_pages))))
        self.result_label.setText(str(result.output))
        self.file_meta.setText(tr("输出：{name}", name=result.output.name))
        self.convert_button.setText(tr("重新识别"))
        self._refresh_controls()

    def _conversion_failed(self, error: object) -> None:
        memory_failure = isinstance(error, MemoryConversionError)
        message = str(error)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label.setStyleSheet(f"color:{C['danger']};")
        memory_error = memory_failure or message.startswith("识别内存不足")
        title = tr("识别内存不足") if memory_error else tr("识别失败")
        self.status_label.setText("●  " + title)
        self.suspect_summary.setText(
            tr("请关闭其他程序后重试") if memory_error else tr("请查看日志中的最后一条错误")
        )
        self._refresh_controls()
        QMessageBox.critical(self, title, message)

    def _cancel_conversion(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel_event.set()
            self._refresh_controls()
            self.status_label.setText(tr("●  正在取消…"))

    def _conversion_cancelled(self) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_label.setText(tr("●  已取消识别"))
        self.suspect_summary.setText(tr("可重新开始识别"))

    def _open_output_folder(self) -> None:
        if not self.output_path:
            return
        try:
            open_output_folder(self.output_path.parent)
        except (OSError, RuntimeError) as exc:
            self._receive_log(f"打开输出文件夹失败：{exc}")
            QMessageBox.warning(
                self, tr("无法打开输出文件夹"),
                tr("输出目录暂时无法访问，请检查 SD 卡或移动硬盘是否已连接。\n重新连接后可以再次点击打开。\n\n目录：{folder}", folder=self.output_path.parent),
            )

    def _open_result(self) -> None:
        if not self.output_path:
            return
        self._open_score_file(self.output_path)

    def _open_score_file(self, path: Path) -> None:
        musescore = find_musescore(self.config.musescore_path)
        if not musescore:
            QMessageBox.warning(self, tr("未找到 MuseScore"), tr("请安装 MuseScore Studio，或在“设置”中选择 MuseScore4.exe。"))
            self._show_settings()
            return
        try:
            if not path.is_file():
                raise FileNotFoundError(str(path))
            open_in_musescore(musescore, path)
        except OSError as exc:
            QMessageBox.critical(self, tr("无法打开 MuseScore"), str(exc))

    def _switch_page(self, index):
        self.pages.setCurrentIndex(index)
        self.conversion_tab.setChecked(index == 0)
        self.library_tab.setChecked(index == 1)
        if index == 1:
            self.library_page.reload()

    def _restore_score(self, entry, start=False):
        if self.worker and self.worker.isRunning():
            return
        self._set_pdf(Path(entry['pdf']))
        if not self.library_entry or self.library_entry['id'] != entry['id']:
            return
        if entry['versions']:
            version = entry['versions'][0]
            self.output_path = Path(version['path'])
            self.log_path = Path(version['log'])
            self.result_label.setText(str(self.output_path))
            self.status_label.setText('●  ' + tr('已识别'))
            self.progress.setValue(100)
            self._refresh_controls()
        if start:
            self._start_conversion()

    def _library_removed(self, identifier):
        if self.library_entry and self.library_entry['id'] == identifier:
            self._clear_pdf()

    def _open_folder(self, folder):
        try:
            open_output_folder(folder)
        except (OSError, RuntimeError) as exc:
            QMessageBox.warning(self, tr('无法打开输出文件夹'), str(exc))

    def _show_log(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("转换日志"))
        dialog.resize(780, 480)
        dialog.setStyleSheet(STYLE)
        layout = QVBoxLayout(dialog)
        log = QPlainTextEdit()
        log.setReadOnly(True)
        if self.log_path and self.log_path.exists():
            log.setPlainText(self.log_path.read_text(encoding="utf-8", errors="replace"))
        else:
            log.setPlainText("\n".join(self._log_lines) or tr("尚无转换日志。"))
        layout.addWidget(log)
        dialog.exec()

    def _refresh_controls(self) -> None:
        running = self.worker is not None and self.worker.isRunning()
        cancelling = running and self.worker.cancel_event.is_set()
        self.convert_button.setText(
            tr("正在取消…") if cancelling else tr("取消识别") if running else
            tr("重新识别") if self.output_path else tr("开始识别")
        )
        self.convert_button.setEnabled(not cancelling and (running or bool(self.pdf_path)))
        self.open_button.setEnabled(bool(self.output_path) and not running)
        self.folder_button.setEnabled(bool(self.output_path) and not running)
        self.import_stack.setEnabled(not running)
        self.file_panel.setEnabled(not running)
        self.output_edit.setEnabled(not running)
        self.library_page.setEnabled(not running)

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            self._cancel_conversion()
            self.worker.wait(7000)
            if self.worker.isRunning():
                event.ignore()
                return
        super().closeEvent(event)
