import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QStackedWidget, QLineEdit, QScrollArea,
    QComboBox, QCheckBox, QGridLayout, QSizePolicy, QSpacerItem
)

# NavaAI: polished desktop UI prototype. Frontend only; no microphone/backend.
STYLE = """
* { font-family: "Segoe UI"; font-size: 10pt; }
QMainWindow, QWidget#Root, QWidget#Page { background: #0B0F14; color: #E8EDF4; }
QFrame#Sidebar { background: #0E131A; border-right: 1px solid #222C38; }
QLabel#Brand { font-size: 24pt; font-weight: 750; color: #F4F7FB; }
QLabel#BrandMark { color: #8BB7FF; font-size: 19pt; font-weight: 800; }
QLabel#Tagline { color: #7F8B9B; font-size: 8pt; letter-spacing: 1.2px; }
QLabel#PageTitle { font-size: 21pt; font-weight: 700; color: #F3F6FA; }
QLabel#Subtitle, QLabel#Muted { color: #8997A8; }
QLabel#SectionLabel { color: #718094; font-size: 8pt; font-weight: 700; letter-spacing: 1.1px; }
QFrame#Card { background: #121923; border: 1px solid #263241; border-radius: 14px; }
QFrame#ChatSurface { background: #0F151D; border: 1px solid #263241; border-radius: 15px; }
QFrame#Composer { background: #121923; border: 1px solid #2B394A; border-radius: 13px; }
QPushButton { background: #18212C; color: #DCE5F0; border: 1px solid #304052; border-radius: 8px; padding: 10px 13px; }
QPushButton:hover { background: #202D3B; border-color: #526B88; }
QPushButton#Primary { background: #477CE0; color: #FFFFFF; border: 1px solid #6593EB; font-weight: 650; padding: 11px 16px; }
QPushButton#Primary:hover { background: #568BEF; }
QPushButton#Stop { background: #241A20; color: #D9A8B0; border: 1px solid #573943; }
QPushButton#Stop:disabled { background: #151B23; color: #5E6A79; border-color: #27313D; }
QPushButton#Nav { text-align: left; background: transparent; color: #A7B3C2; border: 1px solid transparent; padding: 11px 12px; }
QPushButton#Nav:hover { background: #151F2A; border-color: #263647; }
QPushButton#NavActive { text-align: left; background: #192B42; color: #E0ECFF; border: 1px solid #2D4D73; padding: 11px 12px; font-weight: 650; }
QLineEdit, QComboBox { background: #0F151D; color: #E8EDF4; border: 1px solid #334254; border-radius: 9px; padding: 12px; selection-background-color: #477CE0; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #6695EB; }
QLabel#AssistantBubble { background: #18222E; border: 1px solid #2B3949; border-radius: 12px; padding: 12px 14px; color: #E6EDF5; }
QLabel#UserBubble { background: #244D86; border: 1px solid #3769A8; border-radius: 12px; padding: 12px 14px; color: #FFFFFF; }
QLabel#Status { background: #172820; color: #91D8B2; border: 1px solid #2C5140; border-radius: 9px; padding: 7px 10px; font-weight: 600; }
QLabel#MicCircle { background: #1A2B41; color: #D7E7FF; border: 1px solid #385C87; border-radius: 30px; font-size: 20pt; }
QCheckBox { spacing: 9px; color: #DCE5F0; padding: 5px 0; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: #101720; width: 9px; margin: 2px; border-radius: 4px; }
QScrollBar::handle:vertical { background: #354457; min-height: 30px; border-radius: 4px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

def muted_label(text):
    label = QLabel(text)
    label.setObjectName("Muted")
    label.setWordWrap(True)
    return label

class Card(QFrame):
    def __init__(self, title, description=None):
        super().__init__()
        self.setObjectName("Card")
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(18, 16, 18, 16)
        self.box.setSpacing(9)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 11pt; font-weight: 650; color: #EEF3F9;")
        self.box.addWidget(heading)
        if description:
            self.box.addWidget(muted_label(description))

class NavaAIWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NavaAI")
        self.resize(1360, 860)
        self.setMinimumSize(1020, 680)
        self.history = []

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(246)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 24, 18, 18)
        side.setSpacing(9)

        brand_row = QHBoxLayout()
        mark = QLabel("N")
        mark.setObjectName("BrandMark")
        mark.setFixedSize(38, 38)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setStyleSheet("background:#1B2E47;border:1px solid #355477;border-radius:11px;")
        brand_text = QVBoxLayout()
        brand = QLabel("NavaAI")
        brand.setObjectName("Brand")
        brand.setStyleSheet("font-size:21pt;")
        tagline = QLabel("DESKTOP ASSISTANT")
        tagline.setObjectName("Tagline")
        brand_text.addWidget(brand)
        brand_text.addWidget(tagline)
        brand_row.addWidget(mark)
        brand_row.addLayout(brand_text)
        brand_row.addStretch()
        side.addLayout(brand_row)
        side.addSpacing(22)

        new_button = QPushButton("+   New conversation")
        new_button.setObjectName("Primary")
        new_button.clicked.connect(self.new_conversation)
        side.addWidget(new_button)
        side.addSpacing(23)

        label = QLabel("WORKSPACE")
        label.setObjectName("SectionLabel")
        side.addWidget(label)

        self.nav_buttons = {}
        nav_items = [
            ("Assistant", "◉   Assistant"),
            ("History", "◷   Conversation history"),
            ("Settings", "⚙   Settings"),
            ("System status", "▦   System status"),
            ("About", "ⓘ   About NavaAI"),
        ]
        for name, caption in nav_items:
            button = QPushButton(caption)
            button.setObjectName("NavActive" if name == "Assistant" else "Nav")
            button.clicked.connect(lambda checked=False, n=name: self.navigate(n))
            side.addWidget(button)
            self.nav_buttons[name] = button

        side.addStretch()
        privacy = QFrame()
        privacy.setObjectName("Card")
        privacy_box = QVBoxLayout(privacy)
        privacy_box.setContentsMargins(13, 12, 13, 12)
        privacy_box.setSpacing(6)
        privacy_heading = QLabel("PRIVACY BY DESIGN")
        privacy_heading.setStyleSheet("font-size:8pt;font-weight:700;color:#A8C8F6;letter-spacing:1px;")
        privacy_box.addWidget(privacy_heading)
        privacy_box.addWidget(muted_label("Local-first design concept"))
        side.addWidget(privacy)
        foot = QLabel("NavaAI  ·  Frontend prototype")
        foot.setStyleSheet("color:#718094;font-size:8pt;padding-top:5px;")
        side.addWidget(foot)

        # Main content
        content = QWidget()
        content_box = QVBoxLayout(content)
        content_box.setContentsMargins(30, 25, 30, 24)
        content_box.setSpacing(20)

        header = QHBoxLayout()
        heading_box = QVBoxLayout()
        self.page_title = QLabel("Assistant")
        self.page_title.setObjectName("PageTitle")
        self.page_subtitle = QLabel("A calm, focused space to work with NavaAI.")
        self.page_subtitle.setObjectName("Subtitle")
        heading_box.addWidget(self.page_title)
        heading_box.addWidget(self.page_subtitle)
        header.addLayout(heading_box)
        header.addStretch()
        self.status = QLabel("●  Ready")
        self.status.setObjectName("Status")
        header.addWidget(self.status, 0, Qt.AlignmentFlag.AlignTop)
        content_box.addLayout(header)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_assistant_page())
        self.stack.addWidget(self.build_history_page())
        self.stack.addWidget(self.build_settings_page())
        self.stack.addWidget(self.build_status_page())
        self.stack.addWidget(self.build_about_page())
        content_box.addWidget(self.stack, 1)
        outer.addWidget(sidebar)
        outer.addWidget(content, 1)
        self.navigate("Assistant")

    def build_assistant_page(self):
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        greeting = QVBoxLayout()
        title = QLabel("How can I help?")
        title.setStyleSheet("font-size:16pt;font-weight:650;color:#EEF3F9;")
        sub = muted_label("Ask a question or start a new conversation.")
        greeting.addWidget(title)
        greeting.addWidget(sub)
        layout.addLayout(greeting)

        chat = QFrame()
        chat.setObjectName("ChatSurface")
        chat_box = QVBoxLayout(chat)
        chat_box.setContentsMargins(20, 17, 20, 18)
        chat_box.setSpacing(13)
        top = QHBoxLayout()
        chat_title = QLabel("Conversation")
        chat_title.setStyleSheet("font-size:11pt;font-weight:650;")
        top.addWidget(chat_title)
        top.addStretch()
        self.chat_count = QLabel("New session")
        self.chat_count.setObjectName("Muted")
        top.addWidget(self.chat_count)
        chat_box.addLayout(top)

        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.chat_scroll.setStyleSheet("QScrollArea { background: #0F151D; } QScrollArea QWidget { background: transparent; }")
        self.chat_inner = QWidget()
        self.chat_inner.setStyleSheet("background: transparent;")
        self.chat_messages = QVBoxLayout(self.chat_inner)
        self.chat_messages.setContentsMargins(0, 6, 0, 6)
        self.chat_messages.setSpacing(15)
        self.chat_messages.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_scroll.setWidget(self.chat_inner)
        chat_box.addWidget(self.chat_scroll, 1)
        layout.addWidget(chat, 1)

        self.add_message("NavaAI", "Welcome to NavaAI. Type a message below to preview the conversation interface.")

        voice = QFrame()
        voice.setObjectName("Card")
        voice_row = QHBoxLayout(voice)
        voice_row.setContentsMargins(17, 14, 17, 14)
        voice_row.setSpacing(15)
        mic = QLabel("♩")
        mic.setObjectName("MicCircle")
        mic.setFixedSize(60, 60)
        mic.setAlignment(Qt.AlignmentFlag.AlignCenter)
        voice_row.addWidget(mic)
        voice_copy = QVBoxLayout()
        voice_title = QLabel("Voice input")
        voice_title.setStyleSheet("font-size:11pt;font-weight:650;")
        self.voice_status = QLabel("Ready when you are")
        self.voice_status.setObjectName("Muted")
        self.voice_note = QLabel("Microphone controls are visual only in this build.")
        self.voice_note.setObjectName("Muted")
        voice_copy.addWidget(voice_title)
        voice_copy.addWidget(self.voice_status)
        voice_copy.addWidget(self.voice_note)
        voice_row.addLayout(voice_copy, 1)
        controls = QVBoxLayout()
        self.start_button = QPushButton("Start listening")
        self.start_button.setObjectName("Primary")
        self.start_button.clicked.connect(self.start_preview)
        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_preview)
        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        voice_row.addLayout(controls)
        layout.addWidget(voice)

        composer = QFrame()
        composer.setObjectName("Composer")
        composer_row = QHBoxLayout(composer)
        composer_row.setContentsMargins(8, 7, 8, 7)
        composer_row.setSpacing(9)
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Message NavaAI…")
        self.message_input.setStyleSheet("QLineEdit { border: none; background: transparent; padding: 10px; }")
        self.message_input.returnPressed.connect(self.send_message)
        send = QPushButton("Send  →")
        send.setObjectName("Primary")
        send.clicked.connect(self.send_message)
        composer_row.addWidget(self.message_input, 1)
        composer_row.addWidget(send)
        layout.addWidget(composer)
        return page

    def build_history_page(self):
        page = QWidget()
        page.setObjectName("Page")
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(muted_label("Messages entered in the current session appear here."))
        self.history_card = Card("Recent messages")
        self.history_box = QVBoxLayout()
        self.history_card.box.addLayout(self.history_box)
        box.addWidget(self.history_card)
        box.addStretch()
        return page

    def build_settings_page(self):
        page = QWidget()
        page.setObjectName("Page")
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(muted_label("Customize the appearance and display preferences of this interface."))
        appearance = Card("Appearance", "Choose a visual theme.")
        row = QHBoxLayout()
        row.addWidget(QLabel("Theme"))
        theme = QComboBox()
        theme.addItems(["Dark (default)", "Midnight blue"])
        row.addWidget(theme, 1)
        appearance.box.addLayout(row)
        box.addWidget(appearance)
        prefs = Card("Preferences", "Display options for this prototype.")
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Language"))
        language = QComboBox()
        language.addItems(["English", "Urdu", "Urdu-English"])
        row2.addWidget(language, 1)
        prefs.box.addLayout(row2)
        prefs.box.addWidget(QCheckBox("Show status indicator"))
        prefs.box.addWidget(QCheckBox("Show privacy label in sidebar"))
        prefs.box.addWidget(QCheckBox("Ask for confirmation before desktop actions"))
        box.addWidget(prefs)
        box.addStretch()
        return page

    def build_status_page(self):
        page = QWidget()
        page.setObjectName("Page")
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        info = muted_label("Prototype overview. These are static indicators, not live system diagnostics.")
        box.addWidget(info)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        data = [
            ("Voice & speech", "Microphone input and transcription", "Not connected"),
            ("Task planning", "Organizing requests into steps", "Planned"),
            ("Screen understanding", "Visual desktop context", "Planned"),
            ("Computer control", "Desktop actions and automation", "Not enabled"),
            ("Verification", "Checking action outcomes", "Planned"),
            ("Privacy", "Local-first approach", "Informational"),
        ]
        for i, (name, desc, state) in enumerate(data):
            card = Card(name, desc)
            state_label = QLabel("•  " + state)
            state_label.setObjectName("Muted")
            card.box.addWidget(state_label)
            grid.addWidget(card, i // 2, i % 2)
        box.addLayout(grid)
        box.addStretch()
        return page

    def build_about_page(self):
        page = QWidget()
        page.setObjectName("Page")
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(Card("NavaAI", "A desktop assistant interface concept designed to make computer interaction feel more natural."))
        box.addWidget(Card("Included in this prototype", "Assistant workspace, session message history, interface preferences, component overview, and project information."))
        box.addWidget(Card("Prototype scope", "This build is frontend-only. It does not record microphone audio, call an AI model, persist conversations between launches, or control desktop applications."))
        box.addStretch()
        return page

    def navigate(self, name):
        indices = {"Assistant": 0, "History": 1, "Settings": 2, "System status": 3, "About": 4}
        subtitles = {
            "Assistant": "A calm, focused space to work with NavaAI.",
            "History": "Review messages entered during this session.",
            "Settings": "Personalize the interface.",
            "System status": "Review the proposed modules and prototype status.",
            "About": "Project information and prototype scope.",
        }
        self.stack.setCurrentIndex(indices[name])
        self.page_title.setText(name)
        self.page_subtitle.setText(subtitles[name])
        for item, button in self.nav_buttons.items():
            button.setObjectName("NavActive" if item == name else "Nav")
            button.style().unpolish(button)
            button.style().polish(button)
        if name == "History":
            self.refresh_history()

    def add_message(self, sender, text):
        row = QHBoxLayout()
        row.setSpacing(10)
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setMaximumWidth(680)
        bubble.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        bubble.setObjectName("UserBubble" if sender == "You" else "AssistantBubble")
        if sender == "You":
            row.addStretch(1)
            row.addWidget(bubble, 0, Qt.AlignmentFlag.AlignRight)
        else:
            avatar = QLabel("N")
            avatar.setFixedSize(30, 30)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet("background:#20334B;color:#CFE2FF;border:1px solid #385777;border-radius:15px;font-weight:700;")
            row.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(bubble, 0, Qt.AlignmentFlag.AlignLeft)
            row.addStretch(1)
        self.chat_messages.addLayout(row)
        self.chat_count.setText("Session · " + str(len(self.history)) + " message" + ("" if len(self.history) == 1 else "s"))

    def send_message(self):
        text = self.message_input.text().strip()
        if not text:
            return
        self.add_message("You", text)
        self.history.append(text)
        self.message_input.clear()
        self.add_message("NavaAI", "This is a frontend preview. AI responses and desktop actions are not connected.")
        self.status.setText("●  Preview")

    def start_preview(self):
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.voice_status.setText("Listening preview active")
        self.voice_note.setText("Preview only — no microphone audio is being recorded.")
        self.status.setText("●  Preview")

    def stop_preview(self):
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.voice_status.setText("Ready when you are")
        self.voice_note.setText("Microphone controls are visual only in this build.")
        self.status.setText("●  Ready")

    def new_conversation(self):
        while self.chat_messages.count():
            item = self.chat_messages.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
            if item.widget():
                item.widget().deleteLater()
        self.history.clear()
        self.add_message("NavaAI", "A new conversation is ready. Type a message below to preview the interface.")
        self.stop_preview()
        self.navigate("Assistant")

    def refresh_history(self):
        while self.history_box.count():
            item = self.history_box.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.history:
            self.history_box.addWidget(muted_label("No messages yet. Try entering a message on the Assistant screen."))
        else:
            for message in reversed(self.history):
                line = QLabel("•   " + message)
                line.setWordWrap(True)
                self.history_box.addWidget(line)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)
    window = NavaAIWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
