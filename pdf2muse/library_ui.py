from pathlib import Path
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                            QLineEdit, QListWidget, QListWidgetItem, QComboBox, QMenu,
                            QMessageBox, QFileDialog, QInputDialog)
from .i18n import tr


def score_icon():
    """Consistent paper glyph; explicit modes prevent Qt tinting selected rows."""
    image = QPixmap(84, 120)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor('#F1EEE7'))
    painter.drawRoundedRect(2, 2, 80, 116, 4, 4)
    painter.setPen(QPen(QColor('#99968F'), 1.5))
    for top in (23, 45, 67, 89):
        for offset in (0, 3, 6, 9, 12):
            painter.drawLine(12, top + offset, 72, top + offset)
    painter.end()
    icon = QIcon()
    for mode in (QIcon.Mode.Normal, QIcon.Mode.Selected, QIcon.Mode.Active, QIcon.Mode.Disabled):
        icon.addPixmap(image, mode, QIcon.State.Off)
        icon.addPixmap(image, mode, QIcon.State.On)
    return icon


class LibraryPage(QWidget):
    importRequested = pyqtSignal()
    scoreRequested = pyqtSignal(object, bool)
    openRequested = pyqtSignal(object)
    folderRequested = pyqtSignal(object)
    removed = pyqtSignal(str)

    def __init__(self, store):
        super().__init__()
        self.store, self.current = store, None
        self.score_icon = score_icon()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        heading = QHBoxLayout()
        title = QLabel(tr('曲谱库'))
        title.setObjectName('section')
        self.count = QLabel()
        self.count.setObjectName('muted')
        add = QPushButton(tr('＋ 导入曲谱'))
        add.setObjectName('primary')
        add.clicked.connect(self.importRequested)
        heading.addWidget(title)
        heading.addWidget(self.count)
        heading.addStretch()
        heading.addWidget(add)
        layout.addLayout(heading)
        split = QHBoxLayout()
        split.setSpacing(24)
        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr('搜索曲谱'))
        self.search.textChanged.connect(self._filter)
        left.addWidget(self.search)
        self.list = QListWidget()
        self.list.setIconSize(QSize(42, 60))
        self.list.setSpacing(5)
        self.list.setStyleSheet('QListWidget{background:transparent;border:0;} QListWidget::item{padding:12px;border-radius:9px;} QListWidget::item:selected{background:#292330;color:#F4F1EA;border:1px solid #746080;}')
        self.list.currentItemChanged.connect(self._select)
        self.list.itemDoubleClicked.connect(lambda _: self._view())
        left.addWidget(self.list, 1)
        self.empty = QLabel(tr('还没有曲谱，导入一份 PDF 开始。'))
        self.empty.setObjectName('muted')
        left.addWidget(self.empty)
        split.addLayout(left, 3)
        self.detail = QWidget()
        self.detail.setMinimumWidth(300)
        self.detail.setMaximumWidth(360)
        right = QVBoxLayout(self.detail)
        right.setContentsMargins(18, 0, 0, 0)
        self.document = QPdfDocument(self)
        view = QPdfView(self)
        view.setDocument(self.document)
        view.setPageMode(QPdfView.PageMode.SinglePage)
        view.setZoomMode(QPdfView.ZoomMode.FitInView)
        right.addWidget(view, 1)
        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setProperty('literalText', True)
        right.addWidget(self.title)
        self.meta = QLabel()
        self.meta.setObjectName('muted')
        right.addWidget(self.meta)
        self.open = QPushButton(tr('在 MuseScore 中打开'))
        self.open.setObjectName('primary')
        self.open.clicked.connect(self._open)
        right.addWidget(self.open)
        actions = QHBoxLayout()
        preview = QPushButton(tr('查看原谱'))
        preview.clicked.connect(self._view)
        more = QPushButton(tr('更多'))
        more.clicked.connect(lambda: self._menu(more))
        actions.addWidget(preview)
        actions.addWidget(more)
        right.addLayout(actions)
        self.version_label = QLabel(tr('打开版本'))
        right.addWidget(self.version_label)
        self.versions = QComboBox()
        right.addWidget(self.versions)
        split.addWidget(self.detail, 2)
        layout.addLayout(split, 1)
        self.reload()

    def reload(self, identifier=None):
        identifier = identifier or (self.current['id'] if self.current else None)
        try:
            entries = self.store.entries()
        except Exception as exc:
            QMessageBox.warning(self, tr('无法读取曲谱库'), str(exc))
            return
        self.list.clear()
        self.count.setText(tr('{count} 份曲谱', count=len(entries)))
        self.empty.setVisible(not entries)
        selected = None
        for entry in entries:
            state = tr('已识别') if entry['versions'] else tr('未识别')
            item = QListWidgetItem(entry['title'] + '\n' + tr('{pages} 页 · {state} · {date}', pages=entry['pages'], state=state, date=entry['updated'][:16].replace('T', ' ')))
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setSizeHint(QSize(200, 88))
            item.setIcon(self.score_icon)
            self.list.addItem(item)
            if entry['id'] == identifier:
                selected = item
        self.list.setCurrentItem(selected or self.list.item(0))
        self.detail.setVisible(bool(entries))
        self._filter(self.search.text())

    def _filter(self, text):
        for index in range(self.list.count()):
            item = self.list.item(index)
            item.setHidden(text.casefold() not in item.data(Qt.ItemDataRole.UserRole)['title'].casefold())

    def _select(self, item, previous=None):
        self.current = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.document.close()
        if not self.current:
            self.detail.setVisible(False)
            return
        self.detail.setVisible(True)
        entry = self.current
        self.title.setText(entry['title'])
        error = self.document.load(entry['pdf'])
        self.meta.setText(tr('{pages} 页', pages=entry['pages']) if error == QPdfDocument.Error.None_ else tr('原谱暂时无法访问'))
        self.versions.clear()
        if entry.get('edited'):
            self.versions.addItem(tr('我的修改 · MuseScore'), entry['edited'])
        for version in entry['versions']:
            self.versions.addItem(tr('识别结果 · {date}', date=version['created'].replace('T', ' ')), version['path'])
        self.version_label.setVisible(bool(self.versions.count()))
        self.versions.setVisible(bool(self.versions.count()))
        self.open.setText(tr('在 MuseScore 中打开') if self.versions.count() else tr('开始识别'))

    def _open(self):
        if self.current:
            if self.versions.count():
                self.openRequested.emit(Path(self.versions.currentData()))
            else:
                self.scoreRequested.emit(self.current, True)

    def _view(self):
        if self.current:
            self.scoreRequested.emit(self.current, False)

    def _menu(self, button):
        if not self.current:
            return
        menu = QMenu(self)
        for key, action in [('重新识别', lambda: self.scoreRequested.emit(self.current, True)),
                            ('打开文件夹', lambda: self.folderRequested.emit(Path(self.current['pdf']).parent)),
                            ('关联 MuseScore 文件', self._associate), ('重命名', self._rename),
                            ('从曲谱库移除', self._remove)]:
            menu.addAction(tr(key), action)
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _update(self, **values):
        try:
            item = self.store.save(dict(self.current, **values))
            self.reload(item['id'])
        except Exception as exc:
            QMessageBox.warning(self, tr('无法保存曲谱库'), str(exc))

    def _associate(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('关联 MuseScore 文件'), '', 'MuseScore (*.mscz *.mscx)')
        if path:
            self._update(edited=path)

    def _rename(self):
        title, ok = QInputDialog.getText(self, tr('重命名'), tr('曲谱名称'), text=self.current['title'])
        if ok and title.strip():
            self._update(title=title.strip())

    def _remove(self):
        if QMessageBox.question(self, tr('从曲谱库移除'), tr('移除这份曲谱？PDF 和识别文件仍保留在本地。')) != QMessageBox.StandardButton.Yes:
            return
        try:
            identifier = self.current['id']
            self.store.remove(identifier)
            self.removed.emit(identifier)
            self.reload()
        except Exception as exc:
            QMessageBox.warning(self, tr('无法保存曲谱库'), str(exc))
