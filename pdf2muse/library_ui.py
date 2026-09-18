from pathlib import Path
from collections import OrderedDict
from threading import Condition
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, QTimer, QSignalBlocker
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtPdf import QPdfDocument
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


class CoverWorker(QThread):
    """One serialized renderer; replace queued requests instead of accumulating them."""
    ready = pyqtSignal(int, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.condition = Condition()
        self.pending = None
        self.stopping = False

    def request(self, generation, path):
        with self.condition:
            self.pending = (generation, path)
            self.condition.notify()

    def stop(self):
        with self.condition:
            self.stopping = True
            self.pending = None
            self.condition.notify()

    def run(self):
        while True:
            with self.condition:
                self.condition.wait_for(lambda: self.stopping or self.pending is not None)
                if self.stopping:
                    return
                generation, path = self.pending
                self.pending = None
            image = None
            # Create, render and destroy the document on this thread only.
            document = QPdfDocument(None)
            try:
                if document.load(path) == QPdfDocument.Error.None_ and document.pageCount():
                    size = document.pagePointSize(0)
                    if size.width() > 0 and size.height() > 0:
                        scale = min(720 / size.width(), 1000 / size.height())
                        image = document.render(0, QSize(max(1, int(size.width()*scale)),
                                                       max(1, int(size.height()*scale))))
                        if image.isNull():
                            image = None
            except Exception:
                image = None
            finally:
                document.close()
                del document
            self.ready.emit(generation, path, image)


class CoverLabel(QLabel):
    def __init__(self):
        super().__init__()
        self.image = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(180, 220)
        self.setStyleSheet('background:#111113;border-radius:12px;')

    def show_image(self, image):
        self.image = image
        self._fit()

    def _fit(self):
        if self.image is not None:
            self.setPixmap(QPixmap.fromImage(self.image).scaled(
                self.size() - QSize(24, 24), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()


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
        self.cover = CoverLabel()
        right.addWidget(self.cover, 1)
        self.cover_cache = OrderedDict()
        self.cover_generation = 0
        self.cover_worker = CoverWorker(self)
        self.cover_worker.ready.connect(self._cover_ready)
        self.cover_worker.start()
        self.cover_timer = QTimer(self)
        self.cover_timer.setSingleShot(True)
        self.cover_timer.setInterval(150)
        self.cover_timer.timeout.connect(self._load_cover)
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
        blocker = QSignalBlocker(self.list)
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
        del blocker
        self._select(self.list.currentItem())
        self.detail.setVisible(bool(entries))
        self._filter(self.search.text())

    def _filter(self, text):
        for index in range(self.list.count()):
            item = self.list.item(index)
            item.setHidden(text.casefold() not in item.data(Qt.ItemDataRole.UserRole)['title'].casefold())

    def _select(self, item, previous=None):
        self.current = item.data(Qt.ItemDataRole.UserRole) if item else None
        self.cover_generation += 1
        self.cover_timer.stop()
        if not self.current:
            self.detail.setVisible(False)
            return
        self.detail.setVisible(True)
        entry = self.current
        self.title.setText(entry['title'])
        self.meta.setText(tr('{pages} 页', pages=entry['pages']))
        self.cover.show_image(None)
        self.cover.clear()
        self.cover.setText(tr('正在加载预览…'))
        self.cover_timer.start()
        self.versions.clear()
        if entry.get('edited'):
            self.versions.addItem(tr('我的修改 · MuseScore'), entry['edited'])
        for version in entry['versions']:
            self.versions.addItem(tr('识别结果 · {date}', date=version['created'].replace('T', ' ')), version['path'])
        self.version_label.setVisible(bool(self.versions.count()))
        self.versions.setVisible(bool(self.versions.count()))
        self.open.setText(tr('在 MuseScore 中打开') if self.versions.count() else tr('开始识别'))

    def _load_cover(self):
        if not self.current:
            return
        path = self.current['pdf']
        if path in self.cover_cache:
            image = self.cover_cache[path]
            self.cover_cache.move_to_end(path)
            self.cover.show_image(image)
        else:
            self.cover_worker.request(self.cover_generation, path)

    def _cover_ready(self, generation, path, image):
        if image is not None:
            self.cover_cache[path] = image
            self.cover_cache.move_to_end(path)
            while len(self.cover_cache) > 12:
                self.cover_cache.popitem(last=False)
        if generation != self.cover_generation or not self.current or path != self.current['pdf']:
            return
        if image is None:
            self.cover.setText(tr('原谱暂时无法访问'))
        else:
            self.cover.show_image(image)

    def shutdown(self):
        self.cover_timer.stop()
        self.cover_worker.stop()
        return self.cover_worker.wait(100)

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
