from __future__ import annotations

import copy
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ValidationConfig:
    auto_fix_threshold: float = .95
    review_threshold: float = .60
    # Explicit user assertion: octave labels are OMR mistakes, pitches already correct.
    confirmed_annotation_only: bool = False
    confirmed_issue_ids: tuple[str, ...] = ()


@dataclass
class Issue:
    id: str
    measure_number: str
    staff: str
    voice: str
    element_type: str
    rule_id: str
    severity: str
    confidence: float
    original_value: object
    suggested_value: object
    message: str
    reason: str
    auto_fixable: bool
    fixed: bool
    source_location: str
    part_id: str
    measure_index: int
    evidence: dict = field(default_factory=dict)
    patches: list = field(default_factory=list)


class Reviewer(Protocol):
    def review(self, issue: Issue, score_context: dict, source_image=None) -> Issue: ...


class RuleReviewer:
    def review(self, issue: Issue, score_context: dict, source_image=None) -> Issue:
        return issue


def read_score(path: Path) -> ET.Element:
    if path.suffix.lower() == '.mxl':
        with zipfile.ZipFile(path) as archive:
            container = ET.fromstring(archive.read('META-INF/container.xml'))
            files = [e.get('full-path') for e in container.iter()
                     if e.tag.split('}')[-1] == 'rootfile'
                     and e.get('media-type') == 'application/vnd.recordare.musicxml+xml']
            if not files:
                raise ValueError('MXL 中没有 MusicXML rootfile')
            info = archive.getinfo(files[0])
            if info.file_size > 64 * 1024 * 1024:
                raise ValueError('MusicXML 超过 64 MB 检查上限')
            root = ET.fromstring(archive.read(info))
    else:
        root = ET.parse(path).getroot()
    if root.tag != 'score-partwise':
        raise ValueError('当前检查器仅支持 score-partwise MusicXML')
    return root


def _pitch(note):
    p = note.find('pitch')
    if p is None:
        return None
    return 12 * (int(p.findtext('octave')) + 1) + {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[p.findtext('step')] + Fraction(p.findtext('alter', '0'))


def inspect(root: ET.Element, config: ValidationConfig) -> tuple[list[Issue], dict]:
    issues = []
    targets = {}
    names = {p.get('id'): ' '.join(p.itertext()).lower() for p in root.findall('part-list/score-part')}
    for part in root.findall('part'):
        pid = part.get('id', '')
        measures = part.findall('measure')
        violin = 'violin' in names.get(pid, '') or '小提琴' in names.get(pid, '')
        usage = Counter((n.findtext('staff', '1'), n.findtext('voice', '1')) for m in measures for n in m.findall('note'))
        clefs = [c for m in measures for c in m.findall('attributes/clef')]
        octaves = Counter(c.findtext('clef-octave-change', '0') for c in clefs)
        divisions, expected = Fraction(1), None
        ties, slurs = {}, {}
        previous_pitch = {}
        signatures = defaultdict(list)
        for mi, measure in enumerate(measures):
            number = measure.get('number', str(mi + 1))
            prefix = f"part[@id='{pid}']/measure[{mi + 1}]"
            def add(rule, element, message, reason, confidence=.8, severity='WARNING', before=None, after='人工核对', staff='1', voice='', location='', safe=False, evidence=None):
                loc = prefix + location
                identity = f'{rule}:{pid}:{mi}:{loc}:{len(issues)}'
                issue = Issue(hashlib.sha256(identity.encode()).hexdigest()[:16], number, staff, voice, element, rule, severity, confidence, before, after, message, reason, safe, False, loc, pid, mi + 1, evidence or {})
                issues.append(issue)
                return issue
            attrs = measure.find('attributes')
            changed_clef = False
            if attrs is not None:
                if attrs.find('divisions') is not None:
                    divisions = Fraction(attrs.findtext('divisions'))
                    if divisions <= 0:
                        raise ValueError(f'{pid} 第 {number} 小节 divisions 无效')
                time = attrs.find('time')
                if time is not None:
                    expected = None if time.find('senza-misura') is not None else sum((sum(Fraction(x) for x in beats.text.split('+')) * 4 / Fraction(unit.text) for beats, unit in zip(time.findall('beats'), time.findall('beat-type'))), Fraction())
                for ci, clef in enumerate(attrs.findall('clef')):
                    octave = clef.find('clef-octave-change')
                    if clef.findtext('sign') == 'G' and clef.findtext('line') == '2' and octave is not None and octave.text not in ('0', None):
                        changed_clef = True
                        safe = config.confirmed_annotation_only
                        issue = add('CLEF_OCTAVE_ANOMALY', 'clef', '高音谱号含八度标记，请对照原谱', '谱号标记与实际 pitch 独立；仅凭音域不能证明应移动或保留音高。', 1.0 if safe else (.88 if violin else .68), before=ET.tostring(clef, encoding='unicode'), after='移除八度标记，保留全部 pitch', staff=clef.get('number', '1'), location=f'/attributes/clef[{ci+1}]', safe=safe, evidence={'instrument': names.get(pid, ''), 'clef_distribution': dict(octaves), 'system_start': measure.find("print[@new-system='yes']") is not None, 'pitch_semantics': 'annotation-only confirmed' if safe else 'unresolved'})
                        targets[issue.id] = (clef, octave)
            cursor = Fraction()
            maximum = Fraction()
            streams = defaultdict(list)
            last_onset = {}
            for ni, element in enumerate(measure):
                if element.tag in ('backup', 'forward'):
                    value = Fraction(element.findtext('duration', '0')) / divisions
                    cursor += -value if element.tag == 'backup' else value
                    if cursor < 0:
                        add('VOICE_ANOMALY', element.tag, '时间游标退到小节开始之前', 'backup 超出已推进时值', .99, 'ERROR', str(cursor), location=f'/{element.tag}[{ni+1}]')
                    maximum = max(maximum, cursor)
                    continue
                if element.tag != 'note' or element.find('grace') is not None:
                    continue
                key = (element.findtext('staff', '1'), element.findtext('voice', '1'))
                duration = Fraction(element.findtext('duration', '0')) / divisions
                chord = element.find('chord') is not None
                onset = last_onset.get(key, cursor) if chord else cursor
                if not chord:
                    last_onset[key] = cursor
                    cursor += duration
                maximum = max(maximum, onset + duration)
                streams[key].append((element, onset, duration, ni + 1, chord))
            pickup = mi == 0 or measure.get('implicit') == 'yes' or measure.get('non-controlling') == 'yes'
            if expected and maximum != expected and not (pickup and maximum < expected):
                add('MEASURE_DURATION', 'measure', f'小节时值 {maximum}，拍号要求 {expected}', '按 duration/divisions 及 backup/forward 计算；未自动增删音符。末小节可能是弱起补足。', .85 if mi == len(measures)-1 else .98, before=str(maximum), after=str(expected))
            if not streams:
                add('MEASURE_DURATION', 'measure', '没有可检查的有时值音符', '可能为空小节、隐藏内容或未支持的记谱', .65)
            for (staff, voice), notes in streams.items():
                intervals = sorted((on, on+d) for n,on,d,idx,ch in notes if not ch)
                for a,b in zip(intervals, intervals[1:]):
                    if b[0] < a[1]:
                        add('VOICE_ANOMALY', 'voice', '同一谱表声部的音符时值重叠', '已排除 chord 与 grace；请核对声部时间线', .95, staff=staff, voice=voice)
                if len(intervals) > 1 and any(b[0] > a[1] for a,b in zip(intervals, intervals[1:])):
                    add('MEASURE_DURATION','voice','声部时间线内部有未写出的空隙','可能由 forward 或短暂分声部造成；不自动补休止符',.65,staff=staff,voice=voice)
                part_total = sum(v for (s,vv),v in usage.items() if s == staff)
                if violin and usage[(staff,voice)] == 1 and part_total > 20 and voice != '1':
                    add('VOICE_ANOMALY', 'voice', '小提琴声部出现孤立的额外 Voice', '可能是合法双音或短暂分声部；只报告', .65, staff=staff, voice=voice)
                active = {}
                for pos,(note,on,d,idx,chord) in enumerate(notes):
                    loc = f'/note-child[{idx}]'
                    for beam in note.findall('beam'):
                        level, value = beam.get('number','1'), beam.text
                        bad = (value == 'begin' and level in active) or (value in ('continue','end') and level not in active) or value not in ('begin','continue','end','forward hook','backward hook')
                        if bad:
                            add('BEAM_STRUCTURE','beam','符杠起止关系不完整','按 staff/voice/beam level 检查；跨小节符杠可能需要人工核对',.82,before=value,staff=staff,voice=voice,location=loc+'/beam')
                        if value == 'begin': active[level] = idx
                        if value == 'end': active.pop(level,None)
                    if note.find('rest') is not None and note.findall('beam') and expected and maximum > expected and 0 < pos < len(notes)-1 and all(notes[j][0].find('pitch') is not None for j in (pos-1,pos+1)):
                        add('SUSPICIOUS_REST','rest','连贯音符之间的符杠休止符伴随小节多拍','符杠中休止符本身合法；多拍与邻近音符共同提高疑点，禁止自动删除',.8,staff=staff,voice=voice,location=loc)
                    pitch = _pitch(note)
                    if pitch is not None:
                        prev = previous_pitch.get((staff,voice))
                        if prev is not None and abs(pitch-prev) >= 12 and changed_clef:
                            add('OCTAVE_JUMP','pitch','谱号变化附近出现大音程','真实八度跳跃合法，仅与八度谱号疑点同时出现才报告',.65,before=str(pitch-prev),staff=staff,voice=voice,location=loc)
                        previous_pitch[(staff,voice)] = pitch
                        accidental = note.findtext('accidental')
                        alters = {'natural':0,'sharp':1,'flat':-1,'double-sharp':2,'flat-flat':-2}
                        if accidental in alters and Fraction(note.findtext('pitch/alter','0')) != alters[accidental]:
                            add('ACCIDENTAL_CONFLICT','accidental','临时升降号与 pitch/alter 不一致','只检查显式符号与音高；不猜测转调或隐藏升降号',.9,before=accidental,staff=staff,voice=voice,location=loc)
                        for tie in note.findall('tie'):
                            tk = (staff,voice,pitch)
                            if tie.get('type') == 'stop':
                                if tk not in ties: add('TIE_SLUR','tie','延音线 stop 找不到同音高 start','可能包含反复跳转或 OMR 错认；仅报告',.7,staff=staff,voice=voice,location=loc)
                                ties.pop(tk,None)
                            elif tie.get('type') == 'start': ties[tk] = (number,mi,loc)
                    for slur in note.findall('notations/slur'):
                        sk = (staff,voice,slur.get('number','1'))
                        if slur.get('type') == 'stop':
                            if sk not in slurs: add('TIE_SLUR','slur','连音线 stop 找不到 start','按声部与编号配对；跨声部连音线需人工判断',.65,staff=staff,voice=voice,location=loc)
                            slurs.pop(sk,None)
                        elif slur.get('type') == 'start': slurs[sk] = (number,mi,loc)
                for level in active:
                    add('BEAM_STRUCTURE','beam','小节结束时符杠尚未闭合','跨小节符杠可以合法，需对照原谱',.65,staff=staff,voice=voice,before=level)
                signature = tuple((str(d), str(_pitch(n)), n.find('rest') is not None) for n,on,d,idx,ch in notes if not ch)
                signatures[(staff,voice,signature)].append((number, mi + 1))
        # Document-level repeated anomaly evidence, never an independent permission to fix.
        for issue in [i for i in issues if i.part_id == pid and i.rule_id == 'CLEF_OCTAVE_ANOMALY']:
            count = sum(i.part_id == pid and i.rule_id == 'CLEF_OCTAVE_ANOMALY' for i in issues)
            issue.evidence['repeated_octave_clefs'] = count
            if count >= 3:
                issue.evidence['systematic_omr_candidate'] = True
                issue.reason += ' 全谱重复出现，属于系统性 OMR 错误候选；仍需确认 pitch 语义。'
        anomalies = [i for i in issues if i.part_id == pid and i.rule_id == 'CLEF_OCTAVE_ANOMALY']
        if len(anomalies) >= 3:
            first = anomalies[0]
            issues.append(Issue(hashlib.sha256(f'systematic:{pid}'.encode()).hexdigest()[:16],first.measure_number,first.staff,'','clef','SYSTEMATIC_OMR_ERROR','INFO',.8,len(anomalies),'逐处对照原谱','八度谱号异常重复出现','文档级候选；重复本身不能证明错误，不自动修改',False,False,first.source_location,pid,first.measure_index,{'measure_numbers':[i.measure_number for i in anomalies]}))
        # Only raise a repeated-pattern warning when a whole phrase differs by
        # an octave AND has independent octave-clef evidence. Octave repeats are legal.
        pattern_groups = defaultdict(list)
        for (staff,voice,signature), positions in signatures.items():
            if len(signature) < 4:
                continue
            normalized = tuple((duration, str(Fraction(pitch) % 12) if pitch != 'None' else pitch, rest) for duration,pitch,rest in signature)
            pattern_groups[(staff,voice,normalized)].append((signature,positions))
        for (staff,voice,_), patterns in pattern_groups.items():
            if len(patterns) < 2:
                continue
            for signature, positions in patterns:
                for number, index in positions:
                    if not any(i.measure_index == index and i.staff == staff for i in anomalies):
                        continue
                    issues.append(Issue(hashlib.sha256(f'pattern:{pid}:{staff}:{voice}:{index}'.encode()).hexdigest()[:16],number,staff,voice,'measure','PATTERN_ANOMALY','WARNING',.7,str(signature),'核对重复乐句的音高','重复节奏与音级相同，但音区不同且含八度谱号疑点','可能是合法八度重复；需要原谱确认',False,False,f"part[@id='{pid}']/measure[{index}]",pid,index))
        for (staff,voice,pitch),(number,mi,loc) in ties.items():
            issue = Issue(hashlib.sha256(f'tie:{pid}:{staff}:{voice}:{pitch}'.encode()).hexdigest()[:16],number,staff,voice,'tie','TIE_SLUR','WARNING',.7,str(pitch),'人工核对','延音线 start 没有匹配 stop','线性 XML 顺序未闭合；反复路径需人工判断',False,False,f"part[@id='{pid}']/measure[{mi+1}]"+loc,pid,mi+1)
            issues.append(issue)
        for (staff,voice,slur_number),(number,mi,loc) in slurs.items():
            issues.append(Issue(hashlib.sha256(f'slur:{pid}:{staff}:{voice}:{slur_number}'.encode()).hexdigest()[:16],number,staff,voice,'slur','TIE_SLUR','WARNING',.65,slur_number,'人工核对','连音线 start 没有匹配 stop','跨声部连音线或反复路径可能合法',False,False,f"part[@id='{pid}']/measure[{mi+1}]"+loc,pid,mi+1))
    return issues, targets


def validate_score(source: Path, config: ValidationConfig | None = None, output_stem: Path | None = None) -> dict:
    config = config or ValidationConfig()
    root = read_score(source)
    original = copy.deepcopy(root)
    issues, targets = inspect(root, config)
    for issue in issues:
        if issue.id in config.confirmed_issue_ids and issue.rule_id == 'CLEF_OCTAVE_ANOMALY':
            issue.auto_fixable = True
            issue.confidence = 1.0
            issue.evidence['user_confirmed_annotation_only'] = True
        RuleReviewer().review(issue, {})
        if issue.auto_fixable and issue.confidence >= config.auto_fix_threshold:
            clef, octave = targets[issue.id]
            before = ET.tostring(clef, encoding='unicode')
            clef.remove(octave)
            issue.fixed = True
            issue.patches.append({'operation':'remove-clef-octave-change','location':issue.source_location,'before':before,'after':ET.tostring(clef,encoding='unicode'),'rollback':'use original MusicXML'})
    # Invariant: conservative clef repair cannot change any encoded note pitch.
    if [ET.tostring(p) for p in original.iter('pitch')] != [ET.tostring(p) for p in root.iter('pitch')]:
        raise ValueError('修复改变了 pitch，已拒绝输出')
    remaining, _ = inspect(root, ValidationConfig())
    output = Path(str(output_stem) + '.musicxml') if output_stem else source.with_name(source.stem + '.validated.musicxml')
    report = Path(str(output_stem) + '.validation_report.json') if output_stem else source.with_name(source.stem + '.validation_report.json')
    summary = Path(str(output_stem) + '.validation_summary.txt') if output_stem else source.with_name(source.stem + '.validation_summary.txt')
    result = {'schema_version':1, 'original_file':str(source), 'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'validated_file':str(output), 'report_file':str(report), 'summary_file':str(summary), 'elements_scanned':sum(1 for _ in root.iter()), 'measure_count':len(root.findall('part/measure')), 'auto_fixed':sum(i.fixed for i in issues), 'needs_review':sum(not i.fixed and i.confidence >= config.review_threshold for i in issues), 'warnings':sum(not i.fixed and i.severity == 'WARNING' for i in issues), 'issues':[asdict(i) for i in issues], 'remaining_issues':len(remaining), 'config':asdict(config), 'limitations':['置信度为规则评分，不是统计概率','不检查所有音乐错误；谱号未知语义只报告','小节编号来自 OMR，可能与 PDF 不同','不猜测或修改 pitch、节奏、声部']}
    ET.indent(root)
    ET.ElementTree(root).write(output,encoding='utf-8',xml_declaration=True)
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines = [f"审谱完成：{result['measure_count']} 个声部小节，自动修复 {result['auto_fixed']}，待检查 {result['needs_review']}",f'原始文件：{source}',f'检查结果：{output}', '注意：未报告的问题也可能存在识别错误。', '']
    for i in issues:
        lines.append(f"[{ '已修复' if i.fixed else '待核对' }] {i.part_id} 第 {i.measure_number} 小节 / 谱表 {i.staff} / Voice {i.voice or '-'}\n{i.rule_id} ({i.confidence:.2f})：{i.message}\n原因：{i.reason}\n建议：{i.suggested_value}\n")
    summary.write_text('\n'.join(lines),encoding='utf-8')
    return result
