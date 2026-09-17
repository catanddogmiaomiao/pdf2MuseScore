import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from pdf2muse.tools import find_homr_python
from pdf2muse.ui import SettingsDialog


class PortableTests(unittest.TestCase):
    def test_adjacent_engine_wins_over_development_python(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            engine = root / 'engine' / 'HOMR.exe'
            engine.parent.mkdir()
            engine.touch()
            configured = root / 'python.exe'
            configured.touch()
            with patch.object(sys, 'frozen', True, create=True), patch.object(sys, 'executable', str(root / 'PDF2Muse.exe')):
                self.assertEqual(find_homr_python(configured), engine.resolve())

    def test_bundled_settings_hide_python_and_keep_preference(self):
        app = QApplication.instance() or QApplication([])
        class Config:
            language = 'zh_CN'
            homr_python = Path('old-python.exe')
            musescore_path = None
        config = Config()
        with patch('pdf2muse.ui.find_homr_python', return_value=Path('engine/HOMR.exe')):
            dialog = SettingsDialog(config, None)
        self.assertIsNone(dialog.homr_edit)
        dialog._save()
        self.assertEqual(config.homr_python, Path('old-python.exe'))
        dialog.close()
