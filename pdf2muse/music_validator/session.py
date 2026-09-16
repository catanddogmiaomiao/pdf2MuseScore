"""Human review state. Rebuild every revision from the immutable OMR source."""
import hashlib
import json
from pathlib import Path
from .engine import ValidationConfig, validate_score


class ReviewSession:
    def __init__(self, report_path: Path):
        self.report_path = report_path.resolve()
        self.report = json.loads(report_path.read_text(encoding='utf-8'))
        self.source = Path(self.report['original_file'])
        if not self.source.is_file():
            # A copied report may have been generated on another computer.
            candidate = self.report_path.parent / self.source.name
            if candidate.is_file():
                self.source = candidate
        self._verify_source()
        self.state_path = self.source.with_name(self.source.stem + '.review-state.json')
        self.output_stem = self.source.with_name(self.source.stem + '.reviewed')
        self.fixed = {i['id'] for i in self.report['issues'] if i['fixed']}
        self.dismissed = set()
        self.history = []
        self.remaining = {tuple(k) for k in self.report['remaining_issue_keys']} if 'remaining_issue_keys' in self.report else None
        if self.state_path.exists():
            state = json.loads(self.state_path.read_text(encoding='utf-8'))
            if state.get('original_sha256') != self.report['original_sha256']:
                raise ValueError('审谱状态与原始文件不一致，请使用对应报告')
            self.fixed = set(state['fixed_ids'])
            self.dismissed = set(state['dismissed_ids'])
            self.history = state['history']
        self.output = Path(self.report['validated_file'])
        if self.state_path.exists():
            self._rebuild()

    def _verify_source(self):
        if hashlib.sha256(self.source.read_bytes()).hexdigest() != self.report['original_sha256']:
            raise ValueError('原始 OMR 文件已改变，不能安全应用旧报告的修改')

    def _rebuild(self):
        self._verify_source()
        result = validate_score(self.source, ValidationConfig(confirmed_issue_ids=tuple(sorted(self.fixed)),auto_systematic_clefs=False), self.output_stem)
        self.output = Path(result['validated_file'])
        self.remaining = {tuple(k) for k in result['remaining_issue_keys']}

    def apply(self, issue_id: str, action: str):
        self.apply_many([issue_id], action)

    def apply_many(self, issue_ids, action):
        selected = [i for i in self.report['issues'] if i['id'] in set(issue_ids)]
        if len(selected) != len(set(issue_ids)):
            raise ValueError('问题列表不完整')
        if action not in ('fix','undo','dismiss','restore'):
            raise ValueError('未知审谱操作')
        if action == 'fix' and any(i['rule_id'] != 'CLEF_OCTAVE_ANOMALY' for i in selected):
            raise ValueError('此问题需要在 MuseScore 中人工修改')
        old_fixed, old_dismissed = self.fixed.copy(), self.dismissed.copy()
        ids = {i['id'] for i in selected}
        if action == 'fix':
            self.fixed.update(ids)
            self.dismissed.difference_update(ids)
        elif action == 'undo': self.fixed.difference_update(ids)
        elif action == 'dismiss': self.dismissed.update(ids)
        else: self.dismissed.difference_update(ids)
        try:
            if self.fixed != old_fixed:
                self._rebuild()
            events = [{'issue_id':issue['id'],'action':action,'rule_id':issue['rule_id'], 'source_location':issue['source_location'], 'original_value':issue['original_value'], 'suggested_value':issue['suggested_value'], 'reason':'用户选择谱号修复：仅移除八度标记、保留 pitch' if action == 'fix' else '用户审谱操作'} for issue in selected]
            state = {'original_sha256':self.report['original_sha256'],'fixed_ids':sorted(self.fixed),'dismissed_ids':sorted(self.dismissed),'history':self.history+events,'output_file':str(self.output)}
            temporary = self.state_path.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
            temporary.replace(self.state_path)
            self.history.extend(events)
        except Exception:
            self.fixed, self.dismissed = old_fixed, old_dismissed
            raise

    def status(self, issue):
        if issue['id'] in self.fixed: return '已修复'
        if issue['id'] in self.dismissed: return '已核对'
        if issue['severity'] == 'INFO': return '说明'
        if self.remaining is not None and self.key(issue) not in self.remaining: return '已消除'
        return '待核对'

    @staticmethod
    def key(issue):
        return tuple(str(issue.get(k,'')) for k in ('rule_id','part_id','measure_index','staff','voice','source_location'))

    def groups(self, mode='待核对'):
        grouped = {}
        for issue in self.report['issues']:
            status = self.status(issue)
            if status == '说明': continue
            if mode in ('待核对','已修复','已核对') and status != mode: continue
            if mode == '谱号问题' and issue['rule_id'] != 'CLEF_OCTAVE_ANOMALY': continue
            key = (issue['part_id'],issue['measure_index'],issue['staff'])
            grouped.setdefault(key,[]).append(issue)
        priority = {'CLEF_OCTAVE_ANOMALY':0,'MEASURE_DURATION':1}
        return [sorted(group,key=lambda i:priority.get(i['rule_id'],2)) for group in grouped.values()]
