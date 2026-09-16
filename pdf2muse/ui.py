from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QPointF, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .config import AppConfig
from .converter import ConversionError, ConversionResult, convert_with_audiveris
from .tools import find_audiveris, find_musescore, open_in_musescore


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
        title = QLabel("拖放 PDF 乐谱")
        title.setObjectName("dropTitle")
        layout.addWidget(title, 0, Qt.AlignmentFlag.AlignHCenter)
        subtitle = QLabel("或从电脑中选择文件")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(15)
        self.choose_button = QPushButton("＋    选择 PDF")
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
        self.previous_button = QPushButton("上一页")
        self.previous_button.setFixedHeight(34)
        self.next_button = QPushButton("下一页")
        self.next_button.setFixedHeight(34)
        self.page_label = QLabel("第 0 / 0 页")
        self.page_label.setObjectName("muted")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        change_button = QPushButton("更换 PDF")
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
        self.page_label.setText(f"第 {current + 1 if count else 0} / {count} 页")
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
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, pdf: Path, output_dir: Path, audiveris: Path) -> None:
        super().__init__()
        self.pdf, self.output_dir, self.audiveris = pdf, output_dir, audiveris

    def run(self) -> None:
        try:
            result = convert_with_audiveris(
                self.pdf, self.output_dir, self.audiveris,
                self.log.emit, self.progress.emit,
            )
        except (ConversionError, OSError) as exc:
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent: QWidget) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setMinimumWidth(620)
        self.setStyleSheet(STYLE)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(12)
        heading = QLabel("本地工具路径")
        heading.setObjectName("section")
        layout.addWidget(heading)
        note = QLabel("程序会自动查找；自动检测失败时可在这里手动指定。")
        note.setObjectName("muted")
        layout.addWidget(note)
        layout.addSpacing(8)
        self.audiveris_edit = self._path_row(layout, "Audiveris", config.audiveris_path, "Audiveris.exe")
        self.musescore_edit = self._path_row(layout, "MuseScore Studio", config.musescore_path, "MuseScore4.exe")
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("取消")
        save = QPushButton("保存")
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
        edit.setPlaceholderText("自动检测")
        browse = QPushButton("浏览…")
        browse.clicked.connect(lambda: self._browse(edit, executable))
        row.addWidget(edit, 1)
        row.addWidget(browse)
        layout.addLayout(row)
        return edit

    def _browse(self, edit: QLineEdit, executable: str) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择程序", edit.text(), f"{executable} (*.exe);;程序 (*.exe)")
        if path:
            edit.setText(path)

    def _save(self) -> None:
        self.config.audiveris_path = Path(self.audiveris_edit.text()) if self.audiveris_edit.text() else None
        self.config.musescore_path = Path(self.musescore_edit.text()) if self.musescore_edit.text() else None
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = AppConfig()
        self.pdf_path: Path | None = None
        self.output_path: Path | None = None
        self.log_path: Path | None = None
        self.worker: ConversionWorker | None = None
        self._log_lines: list[str] = []
        self.setWindowTitle("PDF2Muse")
        self.setMinimumSize(980, 680)
        self.resize(1200, 780)
        self.setStyleSheet(STYLE)
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(34, 24, 34, 18)
        outer.setSpacing(20)
        outer.addLayout(self._header())
        content = QHBoxLayout()
        content.setSpacing(18)
        content.addWidget(self._import_card(), 1)
        content.addLayout(self._right_column(), 1)
        outer.addLayout(content, 1)
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
        subtitle = QLabel("PDF 乐谱转换")
        subtitle.setObjectName("subtitle")
        titles.addWidget(brand)
        titles.addWidget(subtitle)
        settings = QPushButton("设置")
        settings.clicked.connect(self._show_settings)
        row.addWidget(icon)
        row.addSpacing(8)
        row.addLayout(titles)
        row.addStretch()
        row.addWidget(settings)
        return row

    def _card(self) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)
        return frame, layout

    def _import_card(self) -> QFrame:
        frame, layout = self._card()
        self.import_title = QLabel("导入乐谱")
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
        self.file_name = QLabel("尚未选择文件")
        self.file_meta = QLabel("请选择一份 PDF 乐谱")
        self.file_meta.setObjectName("muted")
        file_text.addWidget(self.file_name)
        file_text.addWidget(self.file_meta)
        clear = QPushButton("×")
        clear.setObjectName("link")
        clear.setFixedWidth(34)
        clear.setToolTip("移除文件")
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
        title = QLabel("转换设置")
        title.setObjectName("section")
        layout.addWidget(title)
        layout.addWidget(QLabel("输出格式"))
        self.format_combo = QComboBox()
        self.format_combo.addItem("MusicXML 压缩文件 (.mxl)", "mxl")
        layout.addWidget(self.format_combo)
        layout.addWidget(QLabel("保存位置"))
        path_row = QHBoxLayout()
        self.output_edit = QLineEdit(str(self.config.output_dir or ""))
        self.output_edit.setPlaceholderText("与原文件相同的文件夹")
        browse = QPushButton("选择")
        browse.setFixedWidth(62)
        browse.setToolTip("选择输出文件夹")
        browse.clicked.connect(self._choose_output_dir)
        path_row.addWidget(self.output_edit, 1)
        path_row.addWidget(browse)
        layout.addLayout(path_row)
        self.convert_button = QPushButton("开始识别")
        self.convert_button.setObjectName("primary")
        self.convert_button.clicked.connect(self._start_conversion)
        layout.addWidget(self.convert_button)
        tip = QLabel("转换后可在 MuseScore 中编辑和播放")
        tip.setObjectName("muted")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip)
        column.addWidget(settings)

        status, layout = self._card()
        title = QLabel("识别状态")
        title.setObjectName("section")
        layout.addWidget(title)
        self.status_label = QLabel("●  等待开始")
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
        suspect_row.addWidget(QLabel("可疑小节"))
        suspect_row.addStretch()
        suspect = QLabel("识别完成后显示")
        suspect.setObjectName("muted")
        suspect_row.addWidget(suspect)
        layout.addLayout(suspect_row)
        action_row = QHBoxLayout()
        self.open_button = QPushButton("在 MuseScore 中打开")
        self.open_button.clicked.connect(self._open_result)
        log_button = QPushButton("查看日志 →")
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
        label = QLabel("免费  ·  本地识别  ·  无需上传")
        label.setObjectName("muted")
        row.addWidget(label)
        row.addStretch()
        version = QLabel("PDF2Muse 0.1")
        version.setObjectName("muted")
        row.addWidget(version)
        return footer

    def _choose_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择 PDF 乐谱", "", "PDF 乐谱 (*.pdf)")
        if path:
            self._set_pdf(Path(path))

    def _set_pdf(self, path: Path) -> None:
        if path.suffix.lower() != ".pdf" or not path.is_file():
            QMessageBox.warning(self, "无法导入", "请选择有效的 PDF 文件。")
            return
        old_path = self.pdf_path
        if not self.pdf_preview.load_pdf(path):
            if old_path:
                self.pdf_preview.load_pdf(old_path)
            QMessageBox.warning(self, "无法预览", "无法读取这份 PDF，文件可能损坏或受到密码保护。")
            return
        self.pdf_path = path.resolve()
        self.output_path = None
        self.import_title.setText("乐谱预览")
        self.import_stack.setCurrentWidget(self.pdf_preview)
        self.file_name.setText(path.name)
        self.file_name.setToolTip(str(path))
        size_mb = path.stat().st_size / (1024 * 1024)
        self.file_meta.setText(f"PDF 乐谱  ·  {self.pdf_preview.page_count} 页  ·  {size_mb:.1f} MB  ·  已就绪")
        self.status_label.setText("●  已选择文件")
        self.status_label.setStyleSheet("")
        self.progress.setValue(0)
        self._refresh_controls()

    def _clear_pdf(self) -> None:
        self.pdf_path = self.output_path = None
        self.pdf_preview.clear()
        self.import_title.setText("导入乐谱")
        self.import_stack.setCurrentWidget(self.drop_zone)
        self.file_name.setText("尚未选择文件")
        self.file_meta.setText("请选择一份 PDF 乐谱")
        self.status_label.setText("●  等待开始")
        self.status_label.setStyleSheet("")
        self.progress.setValue(0)
        self._refresh_controls()

    def _choose_output_dir(self) -> None:
        start = self.output_edit.text() or (str(self.pdf_path.parent) if self.pdf_path else "")
        path = QFileDialog.getExistingDirectory(self, "选择保存位置", start)
        if path:
            self.output_edit.setText(path)
            self.config.output_dir = Path(path)

    def _show_settings(self) -> None:
        SettingsDialog(self.config, self).exec()

    def _start_conversion(self) -> None:
        if not self.pdf_path:
            return
        audiveris = find_audiveris(self.config.audiveris_path)
        if not audiveris:
            QMessageBox.warning(self, "未找到 Audiveris", "请安装 Audiveris，或在“设置”中选择 Audiveris.exe。")
            self._show_settings()
            return
        output_dir = Path(self.output_edit.text()).expanduser() if self.output_edit.text().strip() else self.pdf_path.parent
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "无法使用保存位置", str(exc))
            return
        self.config.output_dir = output_dir if self.output_edit.text().strip() else None
        self.status_label.setStyleSheet("")
        self.status_label.setText("●  正在识别乐谱…")
        self.progress.setValue(2)
        self.output_path = None
        self._log_lines = []
        self.worker = ConversionWorker(self.pdf_path, output_dir, audiveris)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.log.connect(self._receive_log)
        self.worker.succeeded.connect(self._conversion_succeeded)
        self.worker.failed.connect(self._conversion_failed)
        self.worker.finished.connect(self._refresh_controls)
        self._refresh_controls()
        self.worker.start()

    def _receive_log(self, line: str) -> None:
        self._log_lines.append(line)
        self._log_lines = self._log_lines[-1000:]

    def _conversion_succeeded(self, result: ConversionResult) -> None:
        self.output_path, self.log_path = result.output, result.log_file
        self.progress.setValue(100)
        self.status_label.setStyleSheet(f"color:{C['accent']};")
        self.status_label.setText(f"●  识别完成  ·  {result.elapsed_seconds:.1f} 秒")
        self.file_meta.setText(f"输出：{result.output.name}")
        self.convert_button.setText("重新识别")
        self._refresh_controls()

    def _conversion_failed(self, message: str) -> None:
        self.progress.setValue(0)
        self.status_label.setStyleSheet(f"color:{C['danger']};")
        self.status_label.setText("●  识别失败")
        self._refresh_controls()
        QMessageBox.critical(self, "识别失败", message)

    def _open_result(self) -> None:
        if not self.output_path:
            return
        musescore = find_musescore(self.config.musescore_path)
        if not musescore:
            QMessageBox.warning(self, "未找到 MuseScore", "请安装 MuseScore Studio，或在“设置”中选择 MuseScore4.exe。")
            self._show_settings()
            return
        try:
            open_in_musescore(musescore, self.output_path)
        except OSError as exc:
            QMessageBox.critical(self, "无法打开 MuseScore", str(exc))

    def _show_log(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("转换日志")
        dialog.resize(780, 480)
        dialog.setStyleSheet(STYLE)
        layout = QVBoxLayout(dialog)
        log = QPlainTextEdit()
        log.setReadOnly(True)
        if self.log_path and self.log_path.exists():
            log.setPlainText(self.log_path.read_text(encoding="utf-8", errors="replace"))
        else:
            log.setPlainText("\n".join(self._log_lines) or "尚无转换日志。")
        layout.addWidget(log)
        dialog.exec()

    def _refresh_controls(self) -> None:
        running = self.worker is not None and self.worker.isRunning()
        self.convert_button.setEnabled(bool(self.pdf_path) and not running)
        self.open_button.setEnabled(bool(self.output_path) and not running)

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "正在识别", "Audiveris 正在识别乐谱，请等待转换完成后再关闭。")
            event.ignore()
        else:
            super().closeEvent(event)
