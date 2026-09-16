import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from pdf2muse.music_validator.engine import validate_score, read_score
from pdf2muse.music_validator.session import ReviewSession
from test_validation import score, note


class ReviewTests(unittest.TestCase):
    def test_automatic_systematic_clefs_and_undo(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'auto.musicxml'
            root=score(note(duration=16),'<clef-octave-change>-1</clef-octave-change>')
            part=root.find('part')
            for number,octave in ((2,1),(3,-1)):
                m=ET.SubElement(part,'measure',number=str(number))
                ET.SubElement(m,'print',{'new-system':'yes'})
                m.append(ET.fromstring(f'<attributes><clef><sign>G</sign><line>2</line><clef-octave-change>{octave}</clef-octave-change></clef></attributes>'))
                m.append(ET.fromstring(note(duration=16)))
            ET.ElementTree(root).write(source)
            report=validate_score(source)
            self.assertEqual(report['auto_fixed'],3)
            session=ReviewSession(Path(report['report_file']))
            session.apply_many(list(session.fixed),'undo')
            self.assertEqual(len(read_score(session.output).findall('.//clef-octave-change')),3)
            root.find('part-list/score-part/part-name').text='Guitar'
            ET.ElementTree(root).write(source)
            self.assertEqual(validate_score(source)['auto_fixed'],0)

    def test_batch_fix_and_undo_preserve_all_pitches(self):
        with tempfile.TemporaryDirectory() as folder:
            source,session=self.make(folder)
            original=[tuple(p.findtext(k) for k in ('step','alter','octave')) for p in read_score(source).iter('pitch')]
            ids=[i['id'] for i in session.report['issues'] if i['rule_id']=='CLEF_OCTAVE_ANOMALY']
            session.apply_many(ids,'fix')
            self.assertEqual(len(session.fixed),2)
            self.assertFalse(read_score(session.output).findall('.//clef-octave-change'))
            self.assertEqual(original,[tuple(p.findtext(k) for k in ('step','alter','octave')) for p in read_score(session.output).iter('pitch')])
            session.apply_many(ids,'undo')
            self.assertEqual(len(read_score(session.output).findall('.//clef-octave-change')),2)

    def test_duplicate_measure_issues_form_one_task(self):
        with tempfile.TemporaryDirectory() as folder:
            source,session=self.make(folder)
            issue=dict(session.report['issues'][0]);issue['id']='extra';issue['rule_id']='BEAM_STRUCTURE'
            session.report['issues'].append(issue)
            self.assertEqual(len(session.groups()),2)

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
