from datetime import datetime
from pathlib import Path
import sys
from PyQt6.QtCore import QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QComboBox, QScrollArea, QWidget
from .licensing import AccountClient, TERMS_VERSION

class AccountTask(QThread):
    done = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, operation, parent):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.done.emit(self.operation())
        except Exception as error:
            self.failed.emit(str(error))

class AccountDialog(QDialog):
    def __init__(self, parent=None, client=None):
        super().__init__(parent)
        self.client = client or AccountClient()
        self.task = None
        self.setWindowTitle('账号与授权 / Account & license')
        self.setMinimumWidth(620)
        self.resize(660, 730)
        outer = QVBoxLayout(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        content = QWidget()
        scroll.setWidget(content)
        outer.addWidget(scroll)
        layout = QVBoxLayout(content)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        note = QLabel('注册即享 30 天试用；US$9.90 一次付款永久使用（税费以收银台为准）。\n'
                      'Register for a 30-day trial. US$9.90 one-time perpetual access; tax shown at checkout.\n'
                      '每 7 天至少联网刷新一次授权。注册需要邮箱验证码；请妥善保管恢复码。\n'
                      'Refresh online at least every 7 days. Verify your email at registration; save the recovery code.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.mode = QComboBox()
        self.mode.addItems(['登录 / Sign in', '注册 / Register', '恢复码找回 / Recovery code', '邮箱重置密码 / Reset by email'])
        layout.addWidget(self.mode)
        self.username = QLineEdit()
        self.username.setPlaceholderText('用户名 / Username: a–z, 0–9, _')
        layout.addWidget(self.username)
        self.email = QLineEdit()
        self.email.setPlaceholderText('注册邮箱 / Email address')
        layout.addWidget(self.email)
        self.send_email = QPushButton('发送邮箱验证码 / Send email code')
        self.send_email.clicked.connect(self._send_email)
        layout.addWidget(self.send_email)
        self.email_code = QLineEdit()
        self.email_code.setPlaceholderText('6 位邮箱验证码 / 6-digit email code')
        self.email_code.setMaxLength(6)
        layout.addWidget(self.email_code)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText('密码 / Password: 12–128 characters')
        layout.addWidget(self.password)
        self.recovery = QLineEdit()
        self.recovery.setPlaceholderText('恢复码 / Recovery code (account recovery only)')
        layout.addWidget(self.recovery)
        self.agree = QCheckBox('我同意服务条款 / I accept the Terms')
        layout.addWidget(self.agree)
        links = QLabel('<a href="https://pdf2muse.top/legal/privacy/">隐私 / Privacy</a> · '
                       '<a href="https://pdf2muse.top/legal/terms/">条款 / Terms</a> · '
                       '<a href="https://pdf2muse.top/legal/refunds/">退款 / Refunds</a>')
        links.setOpenExternalLinks(True)
        layout.addWidget(links)
        self.signin = QPushButton('继续 / Continue')
        self.signin.clicked.connect(self._authenticate)
        layout.addWidget(self.signin)
        self.code = QLineEdit()
        self.code.setPlaceholderText('授权码 / Activation code: P2M-…')
        layout.addWidget(self.code)
        self.activate = QPushButton('使用授权码激活 / Redeem activation code')
        self.activate.clicked.connect(lambda: self._run(lambda: self.client.request('activate', {'code': self.code.text().strip()})))
        layout.addWidget(self.activate)
        self.buy = QPushButton('US$9.90 · 通过 Creem 永久激活 / Buy through Creem')
        self.buy.clicked.connect(self._checkout)
        layout.addWidget(self.buy)
        row = QHBoxLayout()
        self.refresh = QPushButton('刷新授权 / Refresh')
        self.refresh.clicked.connect(lambda: self._run(self.client.refresh))
        self.logout = QPushButton('退出账号 / Sign out')
        self.logout.clicked.connect(lambda: self._run(self.client.logout))
        close = QPushButton('返回 / Back')
        close.clicked.connect(self.accept)
        for button in (self.refresh, self.logout, close):
            row.addWidget(button)
        layout.addLayout(row)
        self._update()
        self.mode.currentIndexChanged.connect(self._update)

    def _update(self):
        payload = self.client.active()
        user = self.client.state.get('user', {})
        if payload:
            label = '永久授权 / Perpetual' if payload['plan'] == 'perpetual' else '试用至 / Trial until ' + datetime.fromtimestamp(payload['trial_until']).strftime('%Y-%m-%d %H:%M')
            self.status.setText(user.get('username', '') + ' · ' + label)
        else:
            self.status.setText('请登录并刷新授权；试用到期后需激活 / Sign in and refresh; activate after trial expiry.')
        busy = bool(self.task and self.task.isRunning())
        for button in (self.signin, self.refresh, self.logout, self.activate, self.buy):
            button.setEnabled(not busy)
        email_mode = self.mode.currentIndex() in (1, 3)
        self.email.setVisible(email_mode)
        self.email_code.setVisible(email_mode)
        self.send_email.setVisible(email_mode)
        self.send_email.setEnabled(not busy)
        self.username.setVisible(self.mode.currentIndex() != 3)
        logged = bool(self.client.state.get('token'))
        self.activate.setEnabled(logged and not busy)
        self.buy.setEnabled(logged and not busy and (not payload or payload['plan'] != 'perpetual'))
        self.refresh.setEnabled(logged and not busy)
        self.logout.setEnabled(logged and not busy)
        self.recovery.setVisible(self.mode.currentIndex() == 2)
        self.agree.setVisible(True)

    def _authenticate(self):
        mode = self.mode.currentIndex()
        if mode == 1 and not self.agree.isChecked():
            QMessageBox.information(self, '条款 / Terms', '请阅读并同意条款 / Please read and accept the terms.')
            return
        body = {'username': self.username.text().strip(), 'password': self.password.text(), 'accept_terms': self.agree.isChecked(), 'terms_version': TERMS_VERSION, 'email': self.email.text().strip(), 'email_code': self.email_code.text().strip()}
        if mode == 2:
            body['recovery_code'] = self.recovery.text().strip()
        endpoint = ('login', 'register', 'recover', 'password-reset')[mode]
        self._run(lambda: self.client.request(endpoint, body))

    def _send_email(self):
        body = {'email': self.email.text().strip(), 'purpose': 'reset' if self.mode.currentIndex() == 3 else 'register'}
        self._run(lambda: self.client.request('email-code', body))

    def _checkout(self):
        if not self.agree.isChecked():
            QMessageBox.information(self, '条款 / Terms', '购买前请阅读并同意销售与退款条款 / Accept the sales and refund terms before purchase.')
            return
        self._run(lambda: self.client.request('checkout', {'accept_terms': True, 'terms_version': TERMS_VERSION}))

    def _run(self, operation):
        if self.task and self.task.isRunning():
            return
        self.task = AccountTask(operation, self)
        self.task.done.connect(self._done)
        self.task.failed.connect(lambda error: QMessageBox.warning(self, '账号服务 / Account service', error))
        self.task.finished.connect(self._update)
        self.task.start()
        self._update()

    def _done(self, result):
        if result and result.get('user'):
            self.password.clear()
            self.recovery.clear()
            self.code.clear()
            self.email_code.clear()
        if result and result.get('expires_in'):
            QMessageBox.information(self, '邮箱验证码 / Email code', '若该邮箱可用于当前操作，验证码已发送，10分钟内有效。60秒后可重发。\nIf eligible, a code was sent. It expires in 10 minutes; wait 60 seconds before resending.')
        if result and result.get('recovery_code'):
            box = QMessageBox(self)
            box.setWindowTitle('请保存恢复码 / Save your recovery code')
            box.setText('恢复码仅显示一次。遗失密码且没有恢复码将无法自助找回账号。\n'
                        'Shown once. You need this code to recover a forgotten password.')
            box.setDetailedText(result['recovery_code'])
            box.setTextInteractionFlags(__import__('PyQt6.QtCore', fromlist=['Qt']).Qt.TextInteractionFlag.TextSelectableByMouse)
            box.exec()
        if result and result.get('checkout_url'):
            QDesktopServices.openUrl(QUrl(result['checkout_url']))

    def reject(self):
        if self.task and self.task.isRunning():
            return
        super().reject()

    def accept(self):
        if self.task and self.task.isRunning():
            return
        super().accept()

def show_legal(parent):
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
    path = root / 'legal' / 'index.html'
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)) if path.exists() else QUrl('https://pdf2muse.top/legal/'))
