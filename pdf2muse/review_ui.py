from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QAbstractItemView)
from .music_validator.session import ReviewSession


class ReviewDialog(QDialog):
    def __init__(self, report_path: Path, open_score, parent=None):
        super().__init__(parent)
        self.session = ReviewSession(report_path)
        self.open_score = open_score
        self.setWindowTitle('审谱工作台')
        self.resize(1080, 700)
        self.setMinimumSize(850, 560)
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        layout.addWidget(self.summary)
        toolbar = QHBoxLayout()
        self.filter = QComboBox()
        self.filter.addItems(['全部问题','待核对','谱号问题','已修复','已核对'])
        self.filter.setCurrentText('待核对')
        self.filter.currentIndexChanged.connect(self.populate)
        toolbar.addWidget(self.filter)
        self.batch = QPushButton('统一处理谱号')
        self.batch.clicked.connect(self.batch_clefs)
        toolbar.addWidget(self.batch)
        self.last_batch = []
        toolbar.addStretch()
        original = QPushButton('打开原始乐谱')
        original.clicked.connect(lambda: self.open_score(self.session.source))
        toolbar.addWidget(original)
        layout.addLayout(toolbar)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['小节 / 谱表','问题','状态'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.change_selection)
        splitter.addWidget(self.table)
        panel = QWidget()
        details_layout = QVBoxLayout(panel)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.PlainText)
        self.details.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.details.setStyleSheet('background:#141416;border:1px solid #35353B;border-radius:12px;padding:20px;font-size:16px;')
        details_layout.addWidget(self.details,1)
        self.feedback = QLabel('')
        self.feedback.setWordWrap(True)
        details_layout.addWidget(self.feedback)
        row = QHBoxLayout()
        self.fix = QPushButton('改为普通高音谱号')
        self.fix.setObjectName('primary')
        self.fix.clicked.connect(self.primary_action)
        row.addWidget(self.fix,1)
        self.dismiss = QPushButton('保留原样')
        self.dismiss.clicked.connect(self.toggle_dismiss)
        row.addWidget(self.dismiss)
        details_layout.addLayout(row)
        self.undo = QPushButton('撤销修改')
        self.undo.setObjectName('link')
        self.undo.clicked.connect(lambda: self.act('undo'))
        details_layout.addWidget(self.undo)
        splitter.addWidget(panel)
        splitter.setSizes([500,550])
        layout.addWidget(splitter,1)
        self.path = QLabel()
        self.path.setWordWrap(True)
        layout.addWidget(self.path)
        footer = QHBoxLayout()
        hint = QLabel('节奏、音高等问题按小节编号在 MuseScore 中修改，请另存为 MSCZ。\n本工具不能自动定位 MuseScore 光标；编号以识别结果为准。')
        hint.setWordWrap(True)
        footer.addWidget(hint,1)
        button = QPushButton('在 MuseScore 中打开处理结果')
        button.clicked.connect(lambda: self.open_score(self.session.output))
        footer.addWidget(button)
        layout.addLayout(footer)
        self.visible = []
        self.populate()

    def populate(self):
        selected = self.current()
        selected_id = selected['id'] if selected else None
        self.table.blockSignals(True)
        self.issue_groups = self.session.groups(self.filter.currentText())
        self.visible = [group[0] for group in self.issue_groups]
        self.table.setRowCount(len(self.visible))
        for row, issue in enumerate(self.visible):
            messages = list(dict.fromkeys(i['message'] for i in self.issue_groups[row]))
            text_summary = messages[0] + (f'（另 {len(messages)-1} 项）' if len(messages)>1 else '')
            for col,text in enumerate([f"{issue['part_id']} · {issue['measure_number']} / {issue['staff']}",text_summary,self.session.status(issue)]):
                self.table.setItem(row,col,QTableWidgetItem(text))
        self.table.blockSignals(False)
        row = next((r for r,i in enumerate(self.visible) if i['id']==selected_id),0)
        if self.visible: self.table.selectRow(row)
        self.select_issue()
        pending = len(self.session.groups())
        self.summary.setText(f'待检查 {pending} 个小节 · 已修复 {len(self.session.fixed)} 处 · 同小节提示已合并')
        self.update_batch()
        self.path.setText(f'处理结果：{self.session.output.name}')
        self.path.setToolTip(str(self.session.output))

    def current(self):
        row = self.table.currentRow()
        return self.visible[row] if hasattr(self,'visible') and 0 <= row < len(self.visible) else None

    def change_selection(self):
        self.select_issue()
        self.update_batch()

    def batch_candidates(self):
        selected = self.current()
        return [i for i in self.session.report['issues'] if i['rule_id']=='CLEF_OCTAVE_ANOMALY'
                and (selected is None or (i['part_id'],i['staff'])==(selected['part_id'],selected['staff']))
                and self.session.status(i)=='待核对']

    def update_batch(self):
        candidates = self.batch_candidates()
        self.batch.setText('撤销这次批量修改' if self.last_batch else f'统一改为普通高音谱号（{len(candidates)} 处）')
        self.batch.setEnabled(bool(candidates or self.last_batch))
        self.batch.setToolTip('当前谱表统一修正谱号，并补偿受影响音符的八度。原谱有合法八度标记时请逐项处理。')

    def batch_clefs(self):
        undo = bool(self.last_batch)
        ids = self.last_batch if undo else [i['id'] for i in self.batch_candidates()]
        if not ids: return
        try:
            self.session.apply_many(ids,'undo' if undo else 'fix')
        except (OSError,ValueError,KeyError) as exc:
            QMessageBox.warning(self,'未能保存修改',str(exc))
            return
        self.last_batch = [] if undo else ids
        self.populate()
        self.feedback.setText('已撤销批量修改。' if undo else f'已处理 {len(ids)} 处谱号，并自动重新检查相关提示。')

    def select_issue(self):
        issue = self.current()
        if not issue:
            self.details.setText('这一组已经检查完了。')
            self.fix.setEnabled(False); self.undo.setEnabled(False); self.dismiss.setEnabled(False)
            self.undo.hide()
            return
        clef = issue['rule_id']=='CLEF_OCTAVE_ANOMALY'
        fixed = issue['id'] in self.session.fixed
        self.fix.setEnabled(not fixed)
        self.fix.setText('改为普通高音谱号' if clef else '在 MuseScore 中检查')
        self.fix.setVisible(not fixed)
        self.undo.setEnabled(fixed)
        self.undo.setVisible(fixed)
        self.dismiss.setEnabled(not fixed)
        self.dismiss.setVisible(not fixed)
        self.dismiss.setText('重新检查' if issue['id'] in self.session.dismissed else ('保留原样' if clef else '已检查，继续'))
        if clef:
            description = '可能多识别了八度标记。\n\n修复时会同时调整对应音符的八度，保持原来的谱面位置。' if not fixed else '已修正谱号，并调整对应音符的八度。'
        else:
            descriptions = {
                'MEASURE_DURATION':'这一小节可能多拍或少拍，请检查音符和休止符的时值。',
                'VOICE_ANOMALY':'这一小节可能分错了声部，请检查同时演奏的音符。',
                'BEAM_STRUCTURE':'符杠连接可能不完整，请对照原谱检查。',
                'SUSPICIOUS_REST':'两个音符之间可能多了休止符，请对照原谱检查。',
                'OCTAVE_JUMP':'这里的音高跳跃较大，请确认是否与原谱一致。',
                'TIE_SLUR':'延音线或连音线可能没有接好，请检查两端。',
                'ACCIDENTAL_CONFLICT':'升降号可能与音高不一致，请对照原谱检查。',
                'PATTERN_ANOMALY':'相似乐句的音区不同，请确认是否与原谱一致。',
                'SYSTEMATIC_OMR_ERROR':'多处谱号带有八度标记，可以在“谱号问题”中逐项检查。',
            }
            description = descriptions.get(issue['rule_id'],'这里可能有识别问题，请对照原谱检查。')
        self.details.setText(f"第 {issue['measure_number']} 小节 · 谱表 {issue['staff']}\n\n{description}")
        group = self.issue_groups[self.table.currentRow()]
        others = list(dict.fromkeys(i['message'] for i in group[1:]))
        if others:
            self.details.setText(self.details.text() + '\n\n本小节还需检查：\n' + '\n'.join(others))

    def primary_action(self):
        issue = self.current()
        if not issue: return
        if issue['rule_id'] == 'CLEF_OCTAVE_ANOMALY': self.act('fix')
        else: self.open_score(self.session.output)

    def act(self, action):
        issue = self.current()
        if not issue: return
        next_id = next((i['id'] for i in self.visible[self.table.currentRow()+1:] if self.session.status(i)=='待核对'),None)
        try:
            if action in ('dismiss','restore'):
                self.session.apply_many([i['id'] for i in self.issue_groups[self.table.currentRow()] if self.session.status(i) not in ('已修复','已消除')],action)
            else:
                self.session.apply(issue['id'],action)
        except (OSError,ValueError,KeyError) as exc:
            QMessageBox.critical(self,'无法保存审谱操作',str(exc))
            return
        self.populate()
        if action in ('fix','dismiss'):
            if next_id:
                for row, candidate in enumerate(self.visible):
                    if candidate['id']==next_id:
                        self.table.selectRow(row)
                        break
            self.feedback.setText('已改为普通高音谱号。可在“已修复”列表撤销。' if action=='fix' else '已记录，继续检查下一项。')
        else:
            self.feedback.setText('已撤销修改。' if action=='undo' else '已恢复为待核对。')

    def toggle_dismiss(self):
        issue = self.current()
        if issue: self.act('restore' if issue['id'] in self.session.dismissed else 'dismiss')
