import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from pdf2muse.music_validator.engine import validate_score, read_score
from pdf2muse.music_validator.session import ReviewSession
from test_validation import score, note


class ReviewTests(unittest.TestCase):
    def make(self, folder):
        source=Path(folder)/'input.musicxml'
        root=score(note(duration=16),'<clef-octave-change>-1</clef-octave-change>')
        m=ET.SubElement(root.find('part'),'measure',number='2')
        m.append(ET.fromstring('<attributes><clef><sign>G</sign><line>2</line><clef-octave-change>1</clef-octave-change></clef></attributes>'))
        m.append(ET.fromstring(note(duration=16)))
        ET.ElementTree(root).write(source)
        result=validate_score(source)
        return source,ReviewSession(Path(result['report_file']))

    def test_selective_fix_undo_and_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            source,session=self.make(folder)
            original=source.read_bytes()
            validated=Path(session.report['validated_file']).read_bytes()
            clefs=[i for i in session.report['issues'] if i['rule_id']=='CLEF_OCTAVE_ANOMALY']
            session.apply(clefs[0]['id'],'fix')
            self.assertEqual(len(read_score(session.output).findall('.//clef-octave-change')),1)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(Path(session.report['validated_file']).read_bytes(),validated)
            session=ReviewSession(session.report_path)
            self.assertEqual(session.status(clefs[0]),'已修复')
            session.apply(clefs[0]['id'],'undo')
            self.assertEqual(len(read_score(session.output).findall('.//clef-octave-change')),2)

    def test_dismiss_restore_does_not_fix(self):
        with tempfile.TemporaryDirectory() as folder:
            source,session=self.make(folder)
            issue=session.report['issues'][0]
            session.apply(issue['id'],'dismiss')
            self.assertEqual(session.status(issue),'已核对')
            session.apply(issue['id'],'restore')
            self.assertEqual(session.status(issue),'待核对')
            self.assertFalse(session.fixed)

    def test_changed_source_rejects_patch(self):
        with tempfile.TemporaryDirectory() as folder:
            source,session=self.make(folder)
            source.write_text('changed')
            with self.assertRaises(ValueError): session.apply(session.report['issues'][0]['id'],'fix')
            self.assertFalse(session.fixed)
