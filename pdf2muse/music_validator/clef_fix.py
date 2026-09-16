"""Normalize octave clefs while preserving their encoded written staff position."""


def compensate_octaves(root, offsets, fixed_clefs):
    changes = []
    for part in root.findall('part'):
        active = {}
        for mi, measure in enumerate(part.findall('measure'),1):
            for ei, element in enumerate(measure,1):
                if element.tag == 'attributes':
                    for clef in element.findall('clef'):
                        staff = clef.get('number','1')
                        # A new clef ends the previous scope, even within a measure.
                        active[staff] = (offsets[id(clef)], fixed_clefs.get(id(clef)))
                elif element.tag == 'note':
                    octave = element.find('pitch/octave')
                    offset, issue = active.get(element.findtext('staff','1'),(0,None))
                    if octave is None or issue is None or offset == 0:
                        continue
                    before = int(octave.text)
                    after = before - offset
                    if not 0 <= after <= 9:
                        raise ValueError('补偿八度超出 MusicXML 音高范围，拒绝修复')
                    octave.text = str(after)
                    patch = {'operation':'compensate-clef-octave','location':f"part[@id='{part.get('id')}']/measure[{mi}]/child[{ei}]/pitch/octave",'before':before,'after':after,'reason':'保持去除八度谱号前的书写音符位置'}
                    issue.patches.append(patch)
                    changes.append(patch)
    return changes
