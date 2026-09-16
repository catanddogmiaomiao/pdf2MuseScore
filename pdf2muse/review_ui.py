from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPlainTextEdit, QPushButton, QSplitter, QTableWidget,
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
        self.filter.currentIndexChanged.connect(self.populate)
        toolbar.addWidget(self.filter)
        toolbar.addStretch()
        original = QPushButton('打开原始 MXL')
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
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        details_layout.addWidget(self.details)
        self.confirm = QCheckBox('已对照原谱：此八度标记错误，音高已正确')
        self.confirm.toggled.connect(self.select_issue)
        details_layout.addWidget(self.confirm)
        self.fix = QPushButton('应用此项谱号修复')
        self.fix.clicked.connect(lambda: self.act('fix'))
        details_layout.addWidget(self.fix)
        row = QHBoxLayout()
        self.undo = QPushButton('撤销此项修复')
        self.undo.clicked.connect(lambda: self.act('undo'))
        self.dismiss = QPushButton('标记已核对')
        self.dismiss.clicked.connect(self.toggle_dismiss)
        row.addWidget(self.undo)
        row.addWidget(self.dismiss)
        details_layout.addLayout(row)
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
        self.confirm.setChecked(False)
        self.select_issue()
        pending = sum(self.session.status(i)=='待核对' for i in self.session.report['issues'])
        self.summary.setText(f'待核对 {pending} · 已修复 {len(self.session.fixed)} · 已核对 {len(self.session.dismissed)}  |  所有操作自动保存，可逐项撤销')
        self.path.setText(f'当前处理结果：{self.session.output}')

    def current(self):
        row = self.table.currentRow()
        return self.visible[row] if hasattr(self,'visible') and 0 <= row < len(self.visible) else None

    def change_selection(self):
        self.confirm.setChecked(False)
        self.select_issue()

    def select_issue(self):
        issue = self.current()
        if not issue:
            self.details.setPlainText('当前筛选条件下没有问题。')
            self.fix.setEnabled(False); self.undo.setEnabled(False); self.dismiss.setEnabled(False)
            self.confirm.setEnabled(False)
            return
        clef = issue['rule_id']=='CLEF_OCTAVE_ANOMALY'
        fixed = issue['id'] in self.session.fixed
        self.confirm.setEnabled(clef and not fixed)
        self.fix.setEnabled(clef and not fixed and self.confirm.isChecked())
        self.undo.setEnabled(fixed)
        self.dismiss.setEnabled(not fixed)
        self.dismiss.setText('恢复待核对' if issue['id'] in self.session.dismissed else '标记已核对')
        action = '对照 PDF 确认八度标记错误且音高正确后，可应用本项修复。' if clef else '在 MuseScore 中找到此小节，核对音符、休止符和声部；修改后可标记已核对。'
        self.details.setPlainText(f"{issue['message']}\n\n位置：{issue['part_id']} 第 {issue['measure_number']} 小节\n谱表：{issue['staff']} · Voice：{issue['voice'] or '-'}\n规则：{issue['rule_id']}\n评分：{issue['confidence']:.2f}（规则评分）\n状态：{self.session.status(issue)}\n\n原因：{issue['reason']}\n\n原值：{issue['original_value']}\n\n建议：{issue['suggested_value']}\n\n你可以做什么：\n{action}\n\n标记已核对仅记录审核状态，不会自动修改乐谱。\n原始 MXL 和转换后的 validated 文件都保留。")

    def act(self, action):
        issue = self.current()
        if not issue: return
        if action == 'fix' and not self.confirm.isChecked(): return
        try:
            self.session.apply(issue['id'],action)
        except (OSError,ValueError,KeyError) as exc:
            QMessageBox.critical(self,'无法保存审谱操作',str(exc))
            return
        self.populate()

    def toggle_dismiss(self):
        issue = self.current()
        if issue: self.act('restore' if issue['id'] in self.session.dismissed else 'dismiss')
