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
        result = validate_score(self.source, ValidationConfig(confirmed_issue_ids=tuple(sorted(self.fixed))), self.output_stem)
        self.output = Path(result['validated_file'])

    def apply(self, issue_id: str, action: str):
        issue = next(i for i in self.report['issues'] if i['id'] == issue_id)
        if action not in ('fix','undo','dismiss','restore'):
            raise ValueError('未知审谱操作')
        if action == 'fix' and issue['rule_id'] != 'CLEF_OCTAVE_ANOMALY':
            raise ValueError('此问题需要在 MuseScore 中人工修改')
        old_fixed, old_dismissed = self.fixed.copy(), self.dismissed.copy()
        if action == 'fix':
            self.fixed.add(issue_id)
            self.dismissed.discard(issue_id)
        elif action == 'undo': self.fixed.discard(issue_id)
        elif action == 'dismiss': self.dismissed.add(issue_id)
        else: self.dismissed.discard(issue_id)
        try:
            if self.fixed != old_fixed:
                self._rebuild()
            event = {'issue_id':issue_id,'action':action,'rule_id':issue['rule_id'], 'source_location':issue['source_location'], 'original_value':issue['original_value'], 'suggested_value':issue['suggested_value'], 'reason':'用户逐项确认：仅移除八度标记、保留 pitch' if action == 'fix' else '用户审谱操作'}
            state = {'original_sha256':self.report['original_sha256'],'fixed_ids':sorted(self.fixed),'dismissed_ids':sorted(self.dismissed),'history':self.history+[event],'output_file':str(self.output)}
            temporary = self.state_path.with_suffix('.json.tmp')
            temporary.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
            temporary.replace(self.state_path)
            self.history.append(event)
        except Exception:
            self.fixed, self.dismissed = old_fixed, old_dismissed
            raise

    def status(self, issue):
        if issue['id'] in self.fixed: return '已修复'
        if issue['id'] in self.dismissed: return '已核对'
        return '待核对'
