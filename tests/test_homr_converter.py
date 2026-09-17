import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from pdf2muse.converter import ConversionCancelled, ConversionError, convert_with_homr

XML = '<score-partwise><part id="P1"><measure number="1"><note><rest/><duration>1</duration></note></measure></part></score-partwise>'


class ConverterTests(unittest.TestCase):
    def run_fake(self, code, cancel=None):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            pdf = base / '中文 乐谱.pdf'
            pdf.write_bytes(b'%PDF fake')
            script = base / 'fake.py'
            script.write_text(code, encoding='utf-8')
            real_popen = subprocess.Popen

            def start(command, **kwargs):
                return real_popen([sys.executable, '-u', str(script)], **kwargs)

            with patch('pdf2muse.converter.subprocess.Popen', start):
                result = convert_with_homr(pdf, base / '输出', Path(sys.executable), cancel=cancel)
            self.assertEqual(result.output.read_text(), XML)
            self.assertEqual(pdf.read_bytes(), b'%PDF fake')

    def test_complete_merge_and_unicode_path(self):
        self.run_fake(f"from pathlib import Path\nPath('score_0.png').touch()\nPath('score_1.png').touch()\nPath('score_0_merged.musicxml').write_text({XML!r})")

    def test_zero_exit_does_not_hide_failed_page(self):
        with self.assertRaises(ConversionError):
            self.run_fake(f"from pathlib import Path\nPath('score_0.png').touch()\nPath('score_0.musicxml').write_text({XML!r})\nprint('An error occurred while processing score_1.png: failed')")

    def test_partial_output_is_not_exported(self):
        with self.assertRaises(ConversionError):
            self.run_fake(f"from pathlib import Path\nPath('score_0.png').touch()\nPath('score_1.png').touch()\nPath('score_0.musicxml').write_text({XML!r})")

    def test_teaser_image_is_not_an_extra_page(self):
        self.run_fake(f"from pathlib import Path\nPath('score_0.png').touch()\nPath('score_0_teaser.png').touch()\nPath('score_0.musicxml').write_text({XML!r})")

    def test_onnx_memory_failure_has_specific_message(self):
        with self.assertRaisesRegex(ConversionError, '识别内存不足'):
            self.run_fake("print('An error occurred while processing score_0.png: Failed to allocate memory for requested buffer of size 2621440')")

    def test_utf16_native_memory_log(self):
        from pdf2muse.converter import is_memory_error
        self.assertTrue(is_memory_error('\x00'.join('Failed to allocate memory')))
        self.assertFalse(is_memory_error('No noteheads found'))

    def test_cancel_silent_process(self):
        cancel = threading.Event()
        timer = threading.Timer(.5, cancel.set)
        timer.start()
        try:
            with self.assertRaises(ConversionCancelled):
                self.run_fake('import time\ntime.sleep(30)', cancel)
        finally:
            timer.cancel()


if __name__ == '__main__':
    unittest.main()
