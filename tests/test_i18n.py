import ast
import os
import string
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from pdf2muse.config import AppConfig
from pdf2muse.i18n import CATALOG, LANGUAGES, retranslate, set_language, tr
from pdf2muse.converter import MemoryConversionError
from pdf2muse.ui import MainWindow


class Config:
    language = 'zh_CN'
    homr_python = musescore_path = output_dir = None


class I18nTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def tearDown(self):
        set_language('zh_CN')

    def test_catalogs_and_format_fields_are_complete(self):
        def fields(text):
            return {name for _, name, _, _ in string.Formatter().parse(text) if name}
        for key, translations in CATALOG.items():
            self.assertEqual(set(translations), {'en', 'ja', 'ko'})
            for text in translations.values():
                self.assertEqual(fields(key), fields(text), key)
        for name in ('ui.py', 'converter.py', 'library_ui.py'):
            source = Path(__file__).parent.parent / 'pdf2muse' / name
            for node in ast.walk(ast.parse(source.read_text(encoding='utf-8'))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'tr':
                    if node.args and isinstance(node.args[0], ast.Constant):
                        self.assertIn(node.args[0].value, CATALOG)

    def test_live_switch_preserves_task_and_result(self):
        with patch('pdf2muse.ui.AppConfig', Config):
            window = MainWindow()
        output = Path('unchanged.musicxml')
        window.output_path = output
        window.file_name.setText('Settings')
        window.file_name.setProperty('literalText', True)
        class Worker:
            cancel_event = Event()
            def isRunning(self): return True
        worker = Worker()
        window.worker = worker
        window._refresh_controls()
        for language in LANGUAGES:
            set_language(language)
            retranslate(window)
            window._refresh_controls()
            self.assertEqual(window.convert_button.text(), tr('取消识别'))
            self.assertIs(window.worker, worker)
            self.assertEqual(window.output_path, output)
            self.assertEqual(window.file_name.text(), 'Settings')
        window.worker = None
        window.close()

    def test_language_preference_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'settings.ini')
            config = AppConfig.__new__(AppConfig)
            config._settings = QSettings(path, QSettings.Format.IniFormat)
            config.language = 'ko'
            config._settings.sync()
            restored = AppConfig.__new__(AppConfig)
            restored._settings = QSettings(path, QSettings.Format.IniFormat)
            self.assertEqual(restored.language, 'ko')
            restored.language = 'unknown'
            self.assertEqual(restored.language, 'zh_CN')

    def test_memory_error_is_localized_in_every_language(self):
        with patch('pdf2muse.ui.AppConfig', Config):
            window = MainWindow()
        for language in LANGUAGES:
            set_language(language)
            error = MemoryConversionError(tr('识别内存不足，请关闭其他占用内存的程序后重试。日志：{log}', log='test.log'))
            with patch('pdf2muse.ui.QMessageBox.critical'):
                window._conversion_failed(error)
            self.assertEqual(window.status_label.text(), '●  ' + tr('识别内存不足'))
            next_language = 'en' if language != 'en' else 'ja'
            set_language(next_language)
            retranslate(window)
            self.assertEqual(window.status_label.text(), '●  ' + tr('识别内存不足'))
        window.close()
