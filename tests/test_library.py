import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from pdf2muse.library import ScoreLibrary


class LibraryTests(unittest.TestCase):
    def test_owned_copy_dedup_and_versions_survive_source_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'score.pdf'
            source.write_bytes(b'pdf sample')
            store = ScoreLibrary(root / 'library')
            item = store.import_pdf(source, 5)
            self.assertEqual(store.import_pdf(source, 5)['id'], item['id'])
            source.unlink()
            self.assertEqual(Path(item['pdf']).read_bytes(), b'pdf sample')
            output, log = root / 'score.musicxml', root / 'homr.log'
            output.write_text('first', encoding='utf-8')
            log.write_text('log', encoding='utf-8')
            result = SimpleNamespace(output=output, log_file=log)
            item = store.add_result(item, result)
            output.write_text('second', encoding='utf-8')
            item = store.add_result(item, result)
            output.unlink()
            self.assertEqual(len(item['versions']), 2)
            self.assertEqual(Path(item['versions'][1]['path']).read_text(), 'first')
            restored = ScoreLibrary(store.root).entries()[0]
            self.assertEqual(restored['versions'], item['versions'])
            store.remove(item['id'])
            self.assertEqual(store.entries(), [])
            self.assertTrue(Path(item['pdf']).is_file())
            self.assertTrue(Path(item['versions'][0]['path']).is_file())
