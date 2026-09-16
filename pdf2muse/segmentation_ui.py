from pathlib import Path
from io import BytesIO
import json
import hashlib

from PIL import Image
from PyQt6.QtCore import QBuffer, QIODevice, QSize, Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox, QScrollArea

from .segmentation import detect_page, annotate, save_report


class CoordinateCanvas(QLabel):
    def mousePressEvent(self, event):
        if self.pixmap() and self.pixmap().width():
            self.window().adjust_boundary(event.position().x(), event.position().y())


class SegmentationDialog(QDialog):
    def __init__(self, source: Path, directory: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle('谱行与小节 · 切分实验')
        self.resize(1000, 850)
        self.source, self.directory = source, directory
        self.images, self.pages = [], []
        self.document = QPdfDocument(self)
        if self.document.load(str(source)) != QPdfDocument.Error.None_:
            raise ValueError('无法读取 PDF。')
        layout = QVBoxLayout(self)
        self.summary = QLabel('正在分析页面…')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.navigation = QComboBox()
        self.navigation.currentIndexChanged.connect(self.show_page)
        layout.addWidget(self.navigation)
        self.details = QLabel()
        self.details.setWordWrap(True)
        layout.addWidget(self.details)
        scroll = QScrollArea()
        self.canvas = CoordinateCanvas()
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.canvas)
        layout.addWidget(scroll,1)
        layout.addWidget(QLabel('点击小节边界可删除；点击框内可增加边界。仅调整切分，不修改原 PDF。'))
        buttons = QHBoxLayout()
        self.save_button = QPushButton('保存坐标和预览')
        self.save_button.clicked.connect(self.save)
        self.save_button.setEnabled(False)
        buttons.addWidget(self.save_button)
        close = QPushButton('关闭')
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)
        QTimer.singleShot(0,self.analyze_next)

    def analyze_next(self):
        index = len(self.pages)
        if index >= self.document.pageCount():
            report = self.directory / 'coordinates.json'
            if report.exists():
                try:
                    saved = json.loads(report.read_text(encoding='utf-8'))
                    if (saved.get('schema_version') == 1 and
                        saved.get('source_sha256') == hashlib.sha256(self.source.read_bytes()).hexdigest() and
                        len(saved['pages']) == len(self.pages) and
                        all(a['width']==b['width'] and a['height']==b['height'] for a,b in zip(saved['pages'],self.pages))):
                        self.pages = saved['pages']
                except (OSError,ValueError,KeyError,TypeError):
                    pass
            total_rows = sum(len(p['rows']) for p in self.pages)
            total_measures = sum(len(r['measures']) for p in self.pages for r in p['rows'])
            self.summary.setText(f'{len(self.pages)} 页 · {total_rows} 谱行 · {total_measures} 小节（自动检测，请对照框线）')
            self.save_button.setEnabled(True)
            self.navigation.setCurrentIndex(0)
            self.show_page(0)
            return
        try:
            size = self.document.pagePointSize(index)
            qimage = self.document.render(index, QSize(1400,round(1400*size.height()/size.width())))
            if qimage.isNull():
                raise ValueError(f'第 {index+1} 页无法渲染。')
            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            qimage.save(buffer,'PNG')
            image = Image.open(BytesIO(bytes(buffer.data()))).convert('RGB')
            self.images.append(image)
            self.pages.append(detect_page(image,index+1))
            self.navigation.addItem(f'第 {index+1} 页')
            self.summary.setText(f'正在分析第 {index+1} / {self.document.pageCount()} 页…')
            QTimer.singleShot(0,self.analyze_next)
        except (ValueError,OSError) as exc:
            self.summary.setText(str(exc))

    def show_page(self,index):
        if index < 0 or index >= len(self.pages):
            return
        page = self.pages[index]
        self.details.setText(' · '.join(f"第 {r['row']} 行：{len(r['measures'])} 小节" for r in page['rows']) or '未检测到谱行')
        preview = annotate(self.images[index],page)
        data = BytesIO()
        preview.save(data,format='PNG')
        pixmap = QPixmap()
        pixmap.loadFromData(data.getvalue())
        pixmap = pixmap.scaledToWidth(900,Qt.TransformationMode.SmoothTransformation)
        self.canvas.setPixmap(pixmap)
        self.canvas.resize(pixmap.size())

    def adjust_boundary(self,x,y):
        index = self.navigation.currentIndex()
        if not self.save_button.isEnabled() or index < 0:
            return
        page = self.pages[index]
        scale = page['width']/self.canvas.pixmap().width()
        x,y = round(x*scale),round(y*scale)
        for row in page['rows']:
            left,top,right,bottom = row['box']
            if left < x < right and top <= y <= bottom:
                boundaries = row['boundaries']
                near = next((b for b in boundaries[1:-1] if abs(b-x) < 10*scale),None)
                if near is not None:
                    boundaries.remove(near)
                elif min(abs(b-x) for b in boundaries) > row['spacing']*2:
                    boundaries.append(x)
                    boundaries.sort()
                row['manually_adjusted'] = True
                row['measures'] = [dict(column=j+1,box=[a,top,b,bottom]) for j,(a,b) in enumerate(zip(boundaries,boundaries[1:]))]
                self.show_page(index)
                count = sum(len(r['measures']) for p in self.pages for r in p['rows'])
                self.summary.setText(f'已调整切分 · 全谱 {count} 小节')
                break

    def save(self):
        try:
            save_report(self.source,self.pages,self.directory)
            for image,page in zip(self.images,self.pages):
                annotate(image,page).save(self.directory/f"page-{page['page']:02d}.png")
            self.summary.setText(f'已保存：{self.directory}')
        except OSError as exc:
            self.summary.setText(f'保存失败：{exc}')
