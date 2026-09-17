import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
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
            window.library_page.document.close()
            window.close()
            window.deleteLater()
            self.app.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
