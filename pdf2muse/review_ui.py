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
        self.visible = []
        for issue in self.session.report['issues']:
            status = self.session.status(issue)
            mode = self.filter.currentText()
            if mode in ('待核对','已修复','已核对') and status != mode: continue
            if mode == '谱号问题' and issue['rule_id'] != 'CLEF_OCTAVE_ANOMALY': continue
            self.visible.append(issue)
        self.table.setRowCount(len(self.visible))
        for row, issue in enumerate(self.visible):
            for col,text in enumerate([f"{issue['part_id']} · {issue['measure_number']} / {issue['staff']}",issue['message'],self.session.status(issue)]):
                self.table.setItem(row,col,QTableWidgetItem(text))
        self.table.blockSignals(False)
        row = next((r for r,i in enumerate(self.visible) if i['id']==selected_id),0)
        if self.visible: self.table.selectRow(row)
        self.select_issue()
        pending = sum(self.session.status(i)=='待核对' for i in self.session.report['issues'])
        self.summary.setText(f'待核对 {pending} · 已修复 {len(self.session.fixed)} · 已核对 {len(self.session.dismissed)}  |  所有操作自动保存，可逐项撤销')
        self.path.setText(f'处理结果：{self.session.output.name}')
        self.path.setToolTip(str(self.session.output))

    def current(self):
        row = self.table.currentRow()
        return self.visible[row] if hasattr(self,'visible') and 0 <= row < len(self.visible) else None

    def change_selection(self):
        self.select_issue()

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
            description = '可能多识别了八度标记。\n\n改为普通高音谱号会去掉标记，音符音高不变。' if not fixed else '已改为普通高音谱号。\n\n音符音高未改变。'
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
