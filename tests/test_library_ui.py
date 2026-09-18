import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
from threading import Event
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPdfWriter, QPainter
from PyQt6.QtCore import QCoreApplication, QEvent
from pdf2muse.library import ScoreLibrary
from pdf2muse.ui import MainWindow
from pdf2muse.i18n import set_language, retranslate


class Config:
    language = 'zh_CN'
    homr_python = musescore_path = output_dir = None


class LibraryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_import_restore_search_language_and_version_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / 'My score.pdf'
            writer = QPdfWriter(str(pdf))
            painter = QPainter(writer)
            painter.drawText(100, 100, 'Music score')
            painter.end()
            del writer
            store = ScoreLibrary(root / 'library')
            with patch('pdf2muse.ui.AppConfig', Config), patch('pdf2muse.ui.ScoreLibrary', return_value=store):
                window = MainWindow()
            window._set_pdf(pdf)
            self.assertIsNotNone(window.library_entry)
            self.assertNotEqual(window.pdf_path, pdf)
            output, log = root / 'result.musicxml', root / 'log.txt'
            output.write_text('<score-partwise/>', encoding='utf-8')
            log.write_text('done', encoding='utf-8')
            window._conversion_succeeded(SimpleNamespace(output=output, log_file=log, elapsed_seconds=1, skipped_pages=()))
            saved = window.library_entry
            window._clear_pdf()
            window._restore_score(saved)
            self.assertTrue(window.output_path.is_file())
            self.assertEqual(window.library_page.list.count(), 1)
            window.library_page.search.setText('does not match')
            self.assertTrue(window.library_page.list.item(0).isHidden())
            window.library_page.search.clear()
            for language in ('en', 'ja', 'ko'):
                set_language(language)
                retranslate(window)
                window.library_page.reload()
                self.assertEqual(window.library_page.current['title'], 'My score')
                self.assertEqual(window.library_page.versions.currentData(), saved['versions'][0]['path'])
            set_language('zh_CN')
            window.pdf_preview.clear()
            window.library_page.cover_worker.stop()
            self.assertTrue(window.library_page.cover_worker.wait(5000))
            window.close()
            window.deleteLater()
            self.app.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_slow_cover_keeps_ui_responsive_and_discards_stale_result(self):
        from PyQt6.QtCore import QTimer
        from PyQt6.QtGui import QImage
        from PyQt6.QtTest import QTest
        from pdf2muse.library_ui import LibraryPage
        entered, release = Event(), Event()

        class SlowDocument:
            class Error:
                None_ = 0
            def __init__(self, parent): pass
            def load(self, path):
                entered.set()
                release.wait(5)
                return 0
            def pageCount(self): return 1
            def pagePointSize(self, page):
                from PyQt6.QtCore import QSizeF
                return QSizeF(200, 300)
            def render(self, page, size):
                image = QImage(size, QImage.Format.Format_RGB32)
                image.fill(0xffffff)
                return image
            def close(self): pass

        entries = [dict(id=str(i), title=str(i), pdf=str(i)+'.pdf', pages=19,
                        versions=[], updated='2026-09-18') for i in range(3)]
        with patch('pdf2muse.library_ui.QPdfDocument', SlowDocument):
            page = LibraryPage(SimpleNamespace(entries=lambda: entries))
            heartbeat = []
            timer = QTimer()
            timer.timeout.connect(lambda: heartbeat.append(1))
            timer.start(10)
            try:
                QTest.qWait(250)
                self.assertTrue(entered.is_set())
                for index in (1, 2, 1, 2):
                    page.list.setCurrentRow(index)
                QTest.qWait(250)
                self.assertGreater(len(heartbeat), 10)
                self.assertEqual(page.current['id'], '2')
                self.assertIsNone(page.cover.image)
                release.set()
                for _ in range(40):
                    QTest.qWait(50)
                    if page.cover.image is not None:
                        break
                self.assertIsNotNone(page.cover.image)
                self.assertEqual(page.current['id'], '2')
                self.assertLessEqual(len(page.cover_cache), 2)
            finally:
                release.set()
                timer.stop()
                page.cover_worker.stop()
                self.assertTrue(page.cover_worker.wait(5000))
                page.deleteLater()
                self.app.processEvents()

    def test_vector_pdf_cover_has_opaque_white_paper(self):
        from PyQt6.QtTest import QTest
        from pdf2muse.library_ui import LibraryPage
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / 'vector.pdf'
            writer = QPdfWriter(str(pdf))
            painter = QPainter(writer)
            painter.drawText(1000, 1000, 'Black notes on transparent PDF paper')
            painter.end()
            del writer
            entry = dict(id='vector', title='vector', pdf=str(pdf), pages=1,
                         versions=[], updated='2026-09-18')
            page = LibraryPage(SimpleNamespace(entries=lambda: [entry]))
            try:
                for _ in range(100):
                    QTest.qWait(30)
                    if page.cover.image is not None:
                        break
                self.assertIsNotNone(page.cover.image)
                color = page.cover.image.pixelColor(0, 0)
                self.assertEqual((color.red(), color.green(), color.blue(), color.alpha()),
                                 (255, 255, 255, 255))
            finally:
                page.cover_worker.stop()
                self.assertTrue(page.cover_worker.wait(5000))
                page.deleteLater()
                self.app.processEvents()
