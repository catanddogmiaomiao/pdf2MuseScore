import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pdf2muse.tools import open_output_folder


class FolderTests(unittest.TestCase):
    def test_missing_folder_does_not_launch_explorer(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('pdf2muse.tools.os.startfile') as launch:
                with self.assertRaises(FileNotFoundError):
                    open_output_folder(Path(directory) / '已掉线')
                launch.assert_not_called()

    def test_disconnect_during_launch_propagates_to_ui(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch('pdf2muse.tools.os.startfile', side_effect=OSError('device disconnected')):
                with self.assertRaises(OSError):
                    open_output_folder(Path(directory))
