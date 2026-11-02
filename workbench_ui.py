"""NavaAI workbench for the tested, typing-only Gwen runtime."""
import json
import os
from pathlib import Path

from PySide6.QtCore import QProcess, QSettings, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QInputDialog, QSplitter, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)
from project_state import SessionStore, discover_backend, read_backend_info

STYLE = """
* { font-family:"Segoe UI"; font-size:10pt; }
QMainWindow, QWidget#Root, QWidget#Page { background:#F4F3EF; color:#263630; }
QLabel { color:#263630; background:transparent; }
QFrame#Sidebar { background:#23372F; border:0; }
QLabel#Brand { font-family:"Georgia"; font-size:29pt; font-weight:600; color:#FAF8F0; }
QLabel#RailNote { color:#BCCBC2; font-size:9pt; }
QLabel#PageTitle { font-family:"Georgia"; font-size:25pt; color:#253A30; }
QLabel#Muted { color:#647169; }
QLabel#SectionLabel { color:#798177; font-size:9pt; font-weight:600; }
QLabel#Welcome { font-family:"Georgia"; font-size:23pt; color:#253A30; }
QFrame#Card, QFrame#ChatSurface { background:#FFFEFA; border:1px solid #DDDCD3; border-radius:9px; }
QLabel#Status { background:#E8E6DF; color:#596357; border-radius:5px; padding:8px 13px; font-weight:600; }
QLabel#Status[connected="true"] { background:#E2EADF; color:#32563C; }
QPushButton { background:#FFFEFA; color:#314037; border:1px solid #D4D6CB; border-radius:5px; padding:10px 14px; min-height:18px; }
QPushButton:hover { background:#ECEEE5; border-color:#AAB5A3; }
QPushButton:focus { border:2px solid #9B6249; }
QPushButton:disabled { color:#979D94; background:#ECECE5; border-color:#DDDED5; }
QPushButton#Primary { background:#A55036; color:white; border:1px solid #A55036; font-weight:600; }
QPushButton#Primary:hover { background:#8C412C; }
QPushButton#Stop { background:#FFF8F4; color:#914A34; border:1px solid #DFC4B8; }
QPushButton#Nav { text-align:left; background:transparent; color:#D4DED6; border:0; padding:13px; }
QPushButton#Nav:hover { background:#314A3D; }
QPushButton#NavActive { text-align:left; background:#E7EBD9; color:#243C2E; border:0; padding:13px; font-weight:600; }
QPushButton#NewRequest { text-align:left; background:#344D3E; color:#F8F8EE; border:1px solid #56705B; padding:12px; }
QPushButton#Example { text-align:left; padding:11px 14px; background:#F0F1E9; border:0; }
QPushButton#Details { text-align:left; color:#667268; background:transparent; border:0; padding:7px 0; }
QLineEdit, QComboBox { background:#FFFEFA; color:#263630; border:1px solid #C8CFC0; border-radius:6px; padding:12px; min-height:22px; selection-background-color:#CCDABB; }
QLineEdit:focus, QComboBox:focus { border:2px solid #8A9E76; }
QTextEdit, QListWidget { background:#FFFEFA; color:#314037; border:1px solid #D5DACB; border-radius:6px; padding:10px; }
QListWidget::item { padding:9px; }
QListWidget::item:selected { background:#E4EAD8; color:#253A30; }
QCheckBox { color:#314037; spacing:9px; padding:6px 0; }
QScrollArea { border:0; background:transparent; }
QScrollArea > QWidget > QWidget { background:transparent; }
QScrollBar:vertical { background:#ECEDE4; width:8px; }
QScrollBar::handle:vertical { background:#BBC6AE; min-height:30px; border-radius:4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QMessageBox { background:#F4F3EF; }
"""


def muted_label(text):
    label = QLabel(text, objectName='Muted')
    label.setWordWrap(True)
    return label


class Card(QFrame):
    def __init__(self, title, description=None):
        super().__init__(objectName='Card')
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(18, 16, 18, 16)
        self.box.setSpacing(10)
        label = QLabel(title)
        label.setStyleSheet('font-weight:600;font-size:12pt;')
        self.box.addWidget(label)
        if description:
            self.box.addWidget(muted_label(description))


class NavaAIWindow(QMainWindow):
    def __init__(self, connect=True, store=None):
        super().__init__()
        self.setWindowTitle('Nava · Desktop help')
        self.resize(1280, 820)
        self.setMinimumSize(900, 620)
        self.settings = QSettings('NavaAI', 'Workbench')
        self.store = store or SessionStore()
        self.session = self.store.new()
        self.busy = self.ready = self.closing = False
        self.target = None
        self.target_locked = False
        self.backend_pid = None
        self.proc = None
        self.buffer = b''
        self.logfile = ''
        self.last_error = ''
        self.confirm_box = None
        root = QWidget(objectName='Root')
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        side = QFrame(objectName='Sidebar')
        side.setFixedWidth(195)
        sidebar = QVBoxLayout(side)
        sidebar.setContentsMargins(18, 25, 18, 20)
        sidebar.addWidget(QLabel('nava', objectName='Brand'))
        sidebar.addWidget(QLabel('Desktop help', objectName='RailNote'))
        sidebar.addSpacing(24)
        self.new_button = QPushButton('+  Start fresh', objectName='NewRequest')
        self.new_button.clicked.connect(self.new_conversation)
        sidebar.addWidget(self.new_button)
        self.nav = {}
        for name in ('Assistant', 'History', 'System & tests', 'Settings'):
            caption = {'Assistant':'Home', 'History':'Past requests', 'System & tests':'Connection', 'Settings':'Preferences'}[name]
            button = QPushButton(caption, objectName='Nav')
            button.clicked.connect(lambda checked=False, n=name: self.navigate(n))
            sidebar.addWidget(button)
            self.nav[name] = button
        sidebar.addStretch()
        sidebar.addWidget(QLabel('Keyboard mode\nVoice is switched off.', objectName='RailNote'))
        sidebar.addSpacing(12)
        sidebar.addWidget(QLabel('Need to stop? Press F8.\nYour history stays on this PC.', objectName='RailNote'))
        outer.addWidget(side)
        content = QVBoxLayout()
        content.setContentsMargins(25, 24, 25, 20)
        header = QHBoxLayout()
        self.title = QLabel('Assistant', objectName='PageTitle')
        header.addWidget(self.title)
        header.addStretch()
        self.status = QLabel('Disconnected', objectName='Status')
        header.addWidget(self.status)
        content.addLayout(header)
        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)
        outer.addLayout(content, 1)
        self.stack.addWidget(self.assistant_page())
        self.stack.addWidget(self.history_page())
        self.stack.addWidget(self.system_page())
        self.stack.addWidget(self.settings_page())
        self.navigate('Assistant')
        self.add_message('NavaAI', 'Ready when you are. Enter a request above, or choose an example to get started.', persist=False)
        QShortcut(QKeySequence('F8'), self, activated=self.stop_task)
        self.shutdown_timer = QTimer(self)
        self.shutdown_timer.setSingleShot(True)
        self.shutdown_timer.timeout.connect(self.force_shutdown)
        if connect:
            QTimer.singleShot(0, self.connect_backend)

    def assistant_page(self):
        page = QWidget(objectName='Page')
        self.home_page = page
        page.setMinimumHeight(660)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(QLabel('What would you like to do?', objectName='Welcome'))
        layout.addWidget(muted_label('Open an app, find something, or ask for help with a task.'))

        window_card = QFrame(objectName='Card')
        row = QHBoxLayout(window_card)
        row.setContentsMargins(16, 11, 16, 11)
        labels = QVBoxLayout()
        labels.addWidget(QLabel('WORKING WINDOW', objectName='SectionLabel'))
        self.target_label = QLabel('Choose a window for clicking, typing or scrolling.')
        self.target_label.setWordWrap(True)
        labels.addWidget(self.target_label)
        row.addLayout(labels, 1)
        self.choose_window = QPushButton('Choose window')
        self.choose_window.setEnabled(False)
        self.choose_window.clicked.connect(lambda: self.write(op='windows'))
        row.addWidget(self.choose_window)
        self.recent_button = QPushButton('Use recent')
        self.recent_button.setToolTip('Follow the last app you selected outside Nava.')
        self.recent_button.clicked.connect(self.use_recent_window)
        row.addWidget(self.recent_button)
        layout.addWidget(window_card)

        request = Card('Your request')
        composer = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText('For example: open Store')
        self.input.setAccessibleName('What would you like Nava to do?')
        self.input.returnPressed.connect(self.send_message)
        self.send = QPushButton('Do this', objectName='Primary')
        self.send.clicked.connect(self.send_message)
        self.send.setEnabled(False)
        composer.addWidget(self.input, 1)
        composer.addWidget(self.send)
        request.box.addLayout(composer)
        examples = QHBoxLayout()
        for caption, command in (('Open an app', 'open '), ('Find something online', 'search '), ('Scroll down', 'scroll down')):
            button = QPushButton(caption, objectName='Example')
            button.clicked.connect(lambda checked=False, text=command: self.prefill(text))
            examples.addWidget(button)
        request.box.addLayout(examples)
        layout.addWidget(request)

        activity = QFrame(objectName='ChatSurface')
        box = QVBoxLayout(activity)
        box.setContentsMargins(18, 14, 18, 14)
        activity_header = QHBoxLayout()
        activity_header.addWidget(QLabel('THIS SESSION', objectName='SectionLabel'))
        activity_header.addStretch()
        self.phase = QLabel('Ready for your next request')
        self.phase.setWordWrap(True)
        activity_header.addWidget(self.phase)
        self.stop_button = QPushButton('Stop · F8', objectName='Stop')
        self.stop_button.clicked.connect(self.stop_task)
        activity_header.addWidget(self.stop_button)
        box.addLayout(activity_header)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setMinimumHeight(130)
        self.chat_scroll.setWidgetResizable(True)
        inner = QWidget()
        self.messages = QVBoxLayout(inner)
        self.messages.setContentsMargins(0, 0, 0, 0)
        self.messages.setSpacing(10)
        self.messages.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_scroll.setWidget(inner)
        box.addWidget(self.chat_scroll, 1)
        layout.addWidget(activity, 1)

        controls = QHBoxLayout()
        controls.addWidget(QLabel('Need help clicking?', objectName='Muted'))
        for caption, command in (('Show click labels', 'Gwen grid'), ('Show screen grid', 'Gwen full grid'), ('Hide labels', 'exit grid')):
            button = QPushButton(caption)
            button.clicked.connect(lambda checked=False, text=command: self.run_shortcut(text))
            controls.addWidget(button)
        controls.addStretch()
        self.grid_state = muted_label('Labels hidden')
        controls.addWidget(self.grid_state)
        layout.addLayout(controls)
        self.details_toggle = QPushButton('Show technical details', objectName='Details')
        self.details_toggle.setCheckable(True)
        self.details_toggle.toggled.connect(self.toggle_details)
        layout.addWidget(self.details_toggle)
        self.trace = QTextEdit()
        self.trace.setReadOnly(True)
        self.trace.setMaximumHeight(125)
        self.trace.hide()
        layout.addWidget(self.trace)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        return scroll

    def toggle_details(self, checked):
        self.trace.setVisible(checked)
        self.home_page.setMinimumHeight(790 if checked else 660)
        self.details_toggle.setText('Hide technical details' if checked else 'Show technical details')

    def run_shortcut(self, text):
        if self.busy or not self.ready:
            return
        self.input.setText(text)
        self.send_message()

    def use_recent_window(self):
        self.target_locked = False
        self.target = getattr(self, 'recent_target', self.target)
        self.update_window_label()

    def update_window_label(self):
        name = (self.target.get('title') or 'Desktop') if self.target else 'Choose a window for clicking, typing or scrolling.'
        self.target_label.setText(name + (' · selected' if self.target_locked else ''))

    def history_page(self):
        page = QWidget(objectName='Page')
        layout = QVBoxLayout(page)
        layout.addWidget(muted_label('Review previous requests and their results. Select a session to read it.'))
        self.history_list = QListWidget()
        self.history_list.currentRowChanged.connect(self.show_history)
        layout.addWidget(self.history_list, 1)
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        layout.addWidget(self.history_text, 2)
        export = QPushButton('Export selected conversation')
        export.clicked.connect(self.export_history)
        layout.addWidget(export)
        return page

    def system_page(self):
        page = QWidget(objectName='Page')
        layout = QVBoxLayout(page)
        card = Card('Connection details', 'Check the local service and open saved test reports.')
        self.runtime_info = muted_label('Not connected')
        card.box.addWidget(self.runtime_info)
        layout.addWidget(card)
        layout.addWidget(muted_label('Test reports · double-click a report to open it.'))
        self.reports = QListWidget()
        self.reports.itemDoubleClicked.connect(self.open_report)
        layout.addWidget(self.reports, 1)
        open_report = QPushButton('Open selected test report')
        open_report.clicked.connect(self.open_report)
        layout.addWidget(open_report)
        logs = QPushButton('Open detailed activity log')
        logs.clicked.connect(lambda: self.open_path(self.logfile))
        layout.addWidget(logs)
        layout.addWidget(muted_label('The service runs locally on this PC. Test reports describe earlier checks and their limits.'))
        return page

    def settings_page(self):
        page = QWidget(objectName='Page')
        layout = QVBoxLayout(page)
        card = Card('Local service location', 'Select the folder containing agent.py, config.json, and its existing .venv.')
        self.backend_path = QLineEdit(self.settings.value('backend', discover_backend()))
        card.box.addWidget(self.backend_path)
        browse = QPushButton('Choose service folder')
        browse.clicked.connect(self.browse_backend)
        card.box.addWidget(browse)
        self.connect_button = QPushButton('Connect', objectName='Primary')
        self.connect_button.clicked.connect(self.connect_backend)
        card.box.addWidget(self.connect_button)
        layout.addWidget(card)
        self.background = QCheckBox('Run supported browser tasks in the background')
        self.background.setChecked(self.settings.value('background', False, type=bool))
        self.background.toggled.connect(lambda value: self.settings.setValue('background', value))
        layout.addWidget(self.background)
        layout.addWidget(muted_label('Supported browser tasks can run without bringing the browser to the front. Other tasks use the selected window.'))
        self.theme = QComboBox()
        self.theme.addItems(['Natural', 'Higher contrast'])
        self.theme.setCurrentIndex(self.settings.value('theme', 0, type=int))
        self.theme.currentIndexChanged.connect(self.apply_theme)
        layout.addWidget(QLabel('Appearance'))
        layout.addWidget(self.theme)
        self.apply_theme(self.theme.currentIndex())
        layout.addWidget(Card('Voice stays off', 'Use the keyboard to enter requests. Voice control is switched off during the current testing phase.'))
        layout.addStretch()
        return page

    def apply_theme(self, index):
        self.settings.setValue('theme', index)
        self.setStyleSheet(STYLE + ('\nQLabel#Muted {color:#394C3C;} QPushButton {border-color:#6C8060;} QLineEdit {border:2px solid #698256;}' if index else ''))

    def navigate(self, name):
        self.stack.setCurrentIndex(list(self.nav).index(name))
        self.title.setText({'Assistant':'Home', 'History':'Past requests', 'System & tests':'Connection', 'Settings':'Preferences'}[name])
        for item, button in self.nav.items():
            button.setObjectName('NavActive' if item == name else 'Nav')
            button.style().unpolish(button); button.style().polish(button)
        if name == 'History':
            self.refresh_history()
        if name == 'System & tests':
            self.refresh_system()

    def prefill(self, text):
        self.input.setText(text)
        self.input.setFocus()

    def add_message(self, role, text, persist=True):
        entry = QFrame()
        entry.setStyleSheet('QFrame {background:#F1F2EA;border:0;border-radius:5px;}')
        box = QVBoxLayout(entry)
        box.setContentsMargins(13, 10, 13, 12)
        box.setSpacing(4)
        caption = QLabel('YOUR REQUEST' if role == 'You' else 'RESULT')
        caption.setStyleSheet('font-size:8pt;font-weight:600;color:#7A8173;')
        box.addWidget(caption)
        label = QLabel(text)
        label.setTextFormat(Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        box.addWidget(label)
        self.messages.addWidget(entry)
        if persist:
            try:
                self.store.add(self.session, role, text)
            except OSError as exc:
                self.trace.append('History could not be saved: ' + str(exc))
        QTimer.singleShot(0, lambda: self.chat_scroll.verticalScrollBar().setValue(self.chat_scroll.verticalScrollBar().maximum()))

    def connect_backend(self):
        if self.busy or (self.proc and self.proc.state() != QProcess.ProcessState.NotRunning):
            self.add_message('NavaAI', 'Already connected or connecting. Close Nava before choosing a different service folder.')
            return
        root = Path(self.backend_path.text().strip())
        python = root / '.venv' / 'Scripts' / 'python.exe'
        if not (root / 'agent.py').is_file() or not python.is_file():
            self.status.setText('Service not found')
            self.last_error = 'Choose the Gwen Doer runtime folder in Settings.'
            self.add_message('NavaAI', self.last_error)
            return
        self.settings.setValue('backend', str(root))
        self.active_backend = str(root)
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(str(root))
        self.proc.setProgram(str(python))
        self.proc.setArguments(['-u', str(Path(__file__).with_name('backend_bridge.py')), '--backend', str(root), '--frontend-pid', str(os.getpid())])
        self.proc.readyReadStandardOutput.connect(self.read_events)
        self.proc.readyReadStandardError.connect(self.read_errors)
        self.proc.finished.connect(self.backend_finished)
        self.proc.errorOccurred.connect(self.process_error)
        self.buffer = b''
        self.status.setText('Connecting…')
        self.proc.start()

    def write(self, **message):
        if self.proc and self.proc.state() == QProcess.ProcessState.Running:
            self.proc.write((json.dumps(message, ensure_ascii=False) + '\n').encode('utf-8'))

    def read_events(self):
        self.buffer += bytes(self.proc.readAllStandardOutput())
        while b'\n' in self.buffer:
            line, self.buffer = self.buffer.split(b'\n', 1)
            try:
                self.on_event(json.loads(line))
            except (ValueError, KeyError) as exc:
                self.trace.append('Invalid backend event: ' + str(exc))

    def read_errors(self):
        text = bytes(self.proc.readAllStandardError()).decode('utf-8', errors='replace').strip()
        if text:
            self.trace.insertPlainText(text + '\n')

    def on_event(self, event):
        kind = event['kind']
        if kind == 'ready':
            self.ready = True
            self.connection_state(True)
            self.choose_window.setEnabled(True)
            self.status.setText('Ready · Keyboard mode')
            self.send.setEnabled(True)
            self.logfile = event['logfile']
            self.backend_pid = event.get('pid')
            self.trace.append(f"Connected. {event['apps']} app entries. Device: {event['device']}. Qwen loads on demand.")
            self.refresh_system()
        elif kind == 'target':
            self.recent_target = event['target']
            if not self.target_locked and not self.busy:
                self.target = event['target']
                self.update_window_label()
        elif kind == 'windows':
            windows = event['windows']
            titles = [w['title'] or 'Desktop' for w in windows]
            names = [title + (' · window ' + str(i+1) if titles.count(title) > 1 else '') for i, title in enumerate(titles)]
            if not names:
                QMessageBox.information(self, 'Choose a window', 'Open the app you want to use, then try again.')
                return
            name, accepted = QInputDialog.getItem(self, 'Choose a window', 'Which window would you like to work in?', names, 0, False)
            if accepted:
                self.target = windows[names.index(name)]
                self.target_locked = True
                self.update_window_label()
        elif kind == 'log':
            self.trace.insertPlainText(event['message'] + '\n')
            self.phase.setText('Working on your request…')
        elif kind == 'evidence':
            # Preserve backend evidence as evidence, without labelling it verified.
            data = event['data']
            if any(key in data for key in ('route', 'action', 'result', 'unexpected_error', 'bridge_error')):
                self.trace.insertPlainText(json.dumps(data, ensure_ascii=False, default=str)[:2500] + '\n')
        elif kind == 'grid':
            self.grid_state.setText(('Click labels on' if event.get('mode') == 'smart' else 'Screen grid on') if event['active'] else 'Labels hidden')
            if event.get('error'):
                self.trace.append(event['error'])
        elif kind == 'choosing':
            self.phase.setText('Choose the matching item in the popup.' )
        elif kind == 'confirm':
            self.phase.setText('Waiting for your confirmation')
            self.confirm_box = QMessageBox(QMessageBox.Icon.Question, 'Confirm desktop action', event['message'], QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, self)
            self.confirm_box.setDefaultButton(QMessageBox.StandardButton.No)
            self.confirm_box.setWindowFlags(self.confirm_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self.confirm_box.finished.connect(self.confirm_reply)
            self.confirm_box.show()
        elif kind == 'stopping':
            if self.confirm_box:
                self.confirm_box.reject()
            self.phase.setText('Stopping… Please wait.')
            self.show_result_window()
        elif kind == 'result':
            self.busy = False
            self.send.setEnabled(self.ready)
            self.new_button.setEnabled(True)
            self.background.setEnabled(True)
            problem = event.get('error') or event['message'].lower().startswith(('could not', 'task failed', 'cannot ', 'browser action stopped', 'browser navigation stopped'))
            self.phase.setText('Stopped' if event.get('stopped') else ('Please try again' if problem else 'Request finished · check the result'))
            self.status.setText('Stopped' if event.get('stopped') else 'Ready · Keyboard mode')
            self.trace.insertPlainText(event['message'] + '\n')
            self.add_message('NavaAI', self.friendly_result(event['message']))
            self.logfile = event.get('logfile', self.logfile)
            self.show_result_window()
        elif kind == 'fatal':
            self.last_error = event['message']
            self.ready = False; self.send.setEnabled(False)
            self.connection_state(False)
            self.choose_window.setEnabled(False)
            self.status.setText('Connection failed')
            self.add_message('NavaAI', event['message'])
            self.show_result_window()
            self.write(op='quit')

    def confirm_reply(self, result):
        self.confirm_box = None
        self.write(op='reply', value=result == int(QMessageBox.StandardButton.Yes))

    def connection_state(self, connected):
        self.status.setProperty('connected', connected)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    @staticmethod
    def friendly_result(text):
        if 'could not observe the target window' in text.lower() or 'did not bring' in text.lower():
            return "I couldn't bring the selected window to the front. Click that window or choose it above, then try again."
        if text == 'Conversation context cleared.':
            return 'Ready for a fresh request.'
        return text

    def send_message(self):
        text = self.input.text().strip()
        if not text or self.busy or not self.ready:
            return
        self.busy = True
        self.send.setEnabled(False)
        self.new_button.setEnabled(False)
        self.background.setEnabled(False)
        self.trace.clear()
        self.phase.setText('Working on your request…')
        self.status.setText('Working…')
        self.add_message('You', text)
        self.input.clear()
        self.allow_backend_focus()
        self.hide()
        self.write(op='run', text=text, background=self.background.isChecked(), expected_target=self.target)

    def allow_backend_focus(self):
        if os.name == 'nt' and self.backend_pid:
            import ctypes
            ctypes.windll.user32.AllowSetForegroundWindow(int(self.backend_pid))

    def stop_task(self):
        self.write(op='stop')
        if self.busy:
            self.phase.setText('Stop requested · waiting for backend')

    def show_result_window(self):
        # Restore without stealing focus from the controlled app.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.show()

    def new_conversation(self):
        if self.busy:
            return
        self.write(op='run', text='/reset') if self.ready else None
        if self.ready:
            self.busy = True; self.send.setEnabled(False); self.new_button.setEnabled(False)
        self.session = self.store.new()
        while self.messages.count():
            self.messages.takeAt(0).widget().deleteLater()
        self.trace.clear()
        self.add_message('NavaAI', 'A fresh start. What would you like to do?', persist=False)
        self.navigate('Assistant')

    def refresh_history(self):
        self.history_list.clear()
        for session in reversed(self.store.sessions):
            self.history_list.addItem(session['created'][:16].replace('T', ' ') + ' · ' + session['title'])

    def show_history(self, row):
        if row < 0:
            self.history_text.clear(); return
        session = self.store.sessions[-1-row]
        self.history_text.setPlainText('\n\n'.join(f"{m['time']} · {m['role']}\n{m['text']}" for m in session['messages']))

    def export_history(self):
        row = self.history_list.currentRow()
        if row < 0:
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Export conversation', 'navaai-conversation.json', 'JSON (*.json)')
        if path:
            try:
                Path(path).write_text(json.dumps(self.store.sessions[-1-row], ensure_ascii=False, indent=2), encoding='utf-8')
            except OSError as exc:
                QMessageBox.warning(self, 'Export failed', str(exc))

    def refresh_system(self):
        try:
            root = getattr(self, 'active_backend', self.backend_path.text())
            info = read_backend_info(root)
            self.runtime_info.setText(f"Runtime: {'connected' if self.ready else 'disconnected'}\nFolder: {root}\nModel: {info['model']}\nModel folder: {'present' if info['model_exists'] else 'missing'}\nConfigured device: {info['config'].get('device')} · loaded only when needed\nVoice: off · Local session history: {self.store.path}")
            self.reports.clear()
            self.reports.addItems(info['reports'])
        except (OSError, ValueError, KeyError) as exc:
            self.runtime_info.setText('Backend unavailable: ' + str(exc))

    def browse_backend(self):
        path = QFileDialog.getExistingDirectory(self, 'Local service location', self.backend_path.text())
        if path:
            self.backend_path.setText(path)

    def open_report(self, *args):
        item = self.reports.currentItem()
        if item:
            self.open_path(str(Path(getattr(self, 'active_backend', self.backend_path.text())) / item.text()))

    def open_path(self, path):
        if path and Path(path).is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))

    def process_error(self, error):
        self.last_error = self.proc.errorString()
        self.trace.append('Backend process: ' + self.last_error)
        if error == QProcess.ProcessError.FailedToStart:
            self.backend_finished()

    def backend_finished(self, *args):
        self.ready = False
        self.connection_state(False)
        self.choose_window.setEnabled(False)
        self.send.setEnabled(False)
        self.new_button.setEnabled(True)
        self.background.setEnabled(True)
        self.status.setText('Disconnected')
        if self.busy:
            self.busy = False
            self.add_message('NavaAI', 'The backend disconnected before returning a result. Inspect the target app before retrying.')
        if self.closing:
            self.shutdown_timer.stop()
            self.close()
        else:
            self.show_result_window()

    def force_shutdown(self):
        if self.proc and self.proc.state() != QProcess.ProcessState.NotRunning:
            # Mouse release was already requested; allow the worker time to stop.
            self.proc.kill()

    def closeEvent(self, event):
        if self.proc and self.proc.state() != QProcess.ProcessState.NotRunning:
            self.closing = True
            self.write(op='quit')
            self.shutdown_timer.start(15000)
            self.hide()
            event.ignore()
        else:
            event.accept()
