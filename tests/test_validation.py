import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from pdf2muse.music_validator.engine import inspect, validate_score, ValidationConfig, read_score


def note(pitch='D', octave=4, duration=4, voice=1, extra=''):
    sound = '<rest/>' if pitch is None else f'<pitch><step>{pitch}</step><octave>{octave}</octave></pitch>'
    return f'<note>{sound}<duration>{duration}</duration><voice>{voice}</voice>{extra}</note>'


def score(content, clef='', implicit=''):
    return ET.fromstring(f'<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>Violin</part-name></score-part></part-list><part id="P1"><measure number="1" {implicit}><attributes><divisions>4</divisions><time><beats>4</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line>{clef}</clef></attributes>{content}</measure></part></score-partwise>')


class ValidationTests(unittest.TestCase):
    def rules(self, root):
        return [i.rule_id for i in inspect(root, ValidationConfig())[0]]

    def test_001_violin_8vb_report_preserves_pitch(self):
        root = score(note(duration=16), '<clef-octave-change>-1</clef-octave-change>')
        self.assertIn('CLEF_OCTAVE_ANOMALY', self.rules(root))
        self.assertFalse(inspect(root, ValidationConfig())[0][0].auto_fixable)

    def test_002_violin_8va_confirmed_annotation_fix(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'input.musicxml'
            root = score(note(duration=16), '<clef-octave-change>1</clef-octave-change>')
            ET.ElementTree(root).write(path)
            original = path.read_bytes()
            result = validate_score(path, ValidationConfig(confirmed_annotation_only=True))
            self.assertEqual(result['auto_fixed'], 1)
            self.assertEqual(path.read_bytes(), original)
            output = read_score(Path(result['validated_file']))
            self.assertIsNone(output.find('.//clef-octave-change'))
            self.assertEqual(output.findtext('.//pitch/octave'), '3')
            self.assertTrue(result['issues'][0]['patches'])

    def test_003_rest_context(self):
        content = note(duration=8, extra='<beam>begin</beam>') + note(None,duration=4,extra='<beam>continue</beam>') + note(duration=8,extra='<beam>end</beam>')
        self.assertIn('SUSPICIOUS_REST',self.rules(score(content)))

    def test_004_orphan_beam(self):
        self.assertIn('BEAM_STRUCTURE', self.rules(score(note(duration=16,extra='<beam>continue</beam>'))))

    def test_005_ambiguous_shift_not_fixed(self):
        root = score(note(octave=3,duration=16),'<clef-octave-change>-1</clef-octave-change>')
        issues,_ = inspect(root, ValidationConfig())
        self.assertFalse(any(i.auto_fixable for i in issues))
        self.assertEqual(root.findtext('.//pitch/octave'),'3')

    def test_006_true_octave_leap(self):
        self.assertNotIn('OCTAVE_JUMP',self.rules(score(note(duration=8)+note(octave=5,duration=8))))

    def test_007_valid_multivoice(self):
        root = score(note(duration=16)+'<backup><duration>16</duration></backup>'+note('F',duration=16,voice=2))
        self.assertNotIn('VOICE_ANOMALY',self.rules(root))
        self.assertNotIn('MEASURE_DURATION',self.rules(root))

    def test_008_pickup(self):
        self.assertNotIn('MEASURE_DURATION',self.rules(score(note(duration=4),implicit='implicit="yes"')))

    def test_chord_grace_tuplet(self):
        root=score(note(duration=8)+note('F',duration=8,extra='<chord/>')+'<note><grace/><pitch><step>C</step><octave>5</octave></pitch></note>'+note(duration=8,extra='<time-modification><actual-notes>3</actual-notes><normal-notes>2</normal-notes></time-modification>'))
        self.assertNotIn('MEASURE_DURATION',self.rules(root))

    def test_legal_beamed_rest(self):
        content=note(duration=4,extra='<beam>begin</beam>')+note(None,duration=4,extra='<beam>continue</beam>')+note(duration=8,extra='<beam>end</beam>')
        self.assertNotIn('SUSPICIOUS_REST',self.rules(score(content)))

    def test_overfull_measure(self):
        self.assertIn('MEASURE_DURATION',self.rules(score(note(duration=20))))

    def test_internal_underfull_measure(self):
        root=score(note(duration=16))
        part=root.find('part')
        m=ET.SubElement(part,'measure',number='2')
        m.append(ET.fromstring(note(duration=4)))
        self.assertIn('MEASURE_DURATION',self.rules(root))


if __name__ == '__main__':
    unittest.main()
