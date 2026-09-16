import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pdf2muse.converter import convert_with_audiveris
from test_validation import score, note
from xml.etree import ElementTree as ET


class Process:
    def __init__(self, command, **kwargs):
        output = Path(command[command.index('-output')+1])
        ET.ElementTree(score(note(duration=16))).write(output/'export.musicxml')
        self.stdout = iter(['Export complete\n'])

    def wait(self):
        return 0


class PipelineTests(unittest.TestCase):
    def test_conversion_preserves_engine_output_and_reviews(self):
        with tempfile.TemporaryDirectory() as temp, patch('pdf2muse.converter.subprocess.Popen',Process):
            folder=Path(temp)
            result=convert_with_audiveris(folder/'score.pdf',folder,folder/'Audiveris.exe')
            self.assertTrue(result.output.exists())
            self.assertTrue(result.original_output.exists())
            self.assertTrue(result.report_file.exists())
            self.assertEqual(len(list((folder/'.pdf2muse').rglob('export.musicxml'))),1)

    def test_validation_failure_keeps_conversion_successful(self):
        with tempfile.TemporaryDirectory() as temp, patch('pdf2muse.converter.subprocess.Popen',Process), patch('pdf2muse.converter.validate_score',side_effect=ValueError('bad review')):
            folder=Path(temp)
            result=convert_with_audiveris(folder/'score.pdf',folder,folder/'Audiveris.exe')
            self.assertEqual(result.output,result.original_output)
            self.assertEqual(result.validation_error,'bad review')
            self.assertIn('bad review',result.log_file.read_text(encoding='utf-8'))
