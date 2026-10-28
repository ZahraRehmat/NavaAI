import subprocess

from voice_panel import VoicePanel
from speech_worker import SpeechWorker

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
)


class NavaAIWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.speech_worker = None

        self.setWindowTitle("NavaAI")
        self.resize(1100, 720)
        self.setMinimumSize(800, 550)

        # Main layout
        root = QWidget()
        self.setCentralWidget(root)

        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 25, 20, 20)

        logo = QLabel("NavaAI")
        logo.setObjectName("Logo")

        tagline = QLabel("YOUR AI ASSISTANT")
        tagline.setObjectName("Muted")

        new_chat = QPushButton("+  New conversation")
        new_chat.clicked.connect(self.clear_chat)

        sidebar_layout.addWidget(logo)
        sidebar_layout.addWidget(tagline)
        sidebar_layout.addSpacing(25)
        sidebar_layout.addWidget(new_chat)
        sidebar_layout.addStretch()

        sidebar_footer = QLabel(
            "Local AI\nVoice-controlled assistant"
        )
        sidebar_footer.setObjectName("Muted")
        sidebar_layout.addWidget(sidebar_footer)

        # Main content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(28, 24, 28, 20)
        content_layout.setSpacing(18)

        # Header
        header = QHBoxLayout()

        title = QLabel("Assistant")
        title.setObjectName("PageTitle")

        self.status = QLabel("● Ready")
        self.status.setObjectName("Status")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status)

        content_layout.addLayout(header)

        # Chat area
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.chat_layout.setSpacing(14)

        self.chat_scroll.setWidget(self.chat_widget)
        content_layout.addWidget(self.chat_scroll, 1)

        # Voice panel
        self.voice_panel = VoicePanel()

        self.voice_panel.listen_requested.connect(
            self.handle_listen_requested
        )
        self.voice_panel.stop_requested.connect(
            self.handle_stop_requested
        )

        content_layout.addWidget(self.voice_panel)

        # Text command input
        input_row = QHBoxLayout()

        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText(
            "Or type a command here..."
        )
        self.command_input.returnPressed.connect(
            self.send_command
        )

        send_button = QPushButton("Send")
        send_button.setObjectName("SendButton")
        send_button.clicked.connect(self.send_command)

        input_row.addWidget(self.command_input, 1)
        input_row.addWidget(send_button)

        content_layout.addLayout(input_row)

        # Add sidebar and content to the window
        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)

        # Welcome message
        self.add_message(
            "NavaAI",
            "Welcome to NavaAI! Click Start listening to record "
            "until you press Stop, or type a command below."
        )

    def add_message(self, sender, message):
        """Display user messages on the right and assistant on the left."""

        row = QHBoxLayout()
        row.setSpacing(10)

        label = QLabel(message)
        label.setWordWrap(True)
        label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        label.setContentsMargins(15, 12, 15, 12)

        if sender == "You":
            label.setMaximumWidth(650)

            label.setStyleSheet("""
                QLabel {
                    background-color: #7545D5;
                    color: white;
                    border-radius: 12px;
                    padding: 12px;
                }
            """)

            row.addStretch()
            row.addWidget(label, 0)

        else:
            label.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Preferred
            )

            label.setStyleSheet("""
                QLabel {
                    background-color: #24222D;
                    color: #F1F0F6;
                    border: 1px solid #353242;
                    border-radius: 12px;
                    padding: 12px;
                }
            """)

            row.addWidget(label, 1)

        self.chat_layout.addLayout(row)

        self.chat_widget.adjustSize()
        self.chat_scroll.verticalScrollBar().setValue(
            self.chat_scroll.verticalScrollBar().maximum()
        )

    def send_command(self):
        """Display a typed command in the frontend demo."""

        command = self.command_input.text().strip()

        if not command:
            return

        self.add_message("You", command)
        self.command_input.clear()

        # Typed commands are still in demo mode.
        self.status.setText("● UI demo")

        self.add_message(
            "NavaAI",
            "Command received by the frontend. "
            "AI execution and computer control are not connected yet."
        )

    def handle_listen_requested(self):
        """Start continuous recording in the background."""

        if (
            self.speech_worker is not None
            and self.speech_worker.isRunning()
        ):
            return

        self.voice_panel.set_transcript(
            "Recording will continue until you press Stop."
        )
        self.voice_panel.set_status("Starting microphone...")
        self.status.setText("● Starting recording")

        self.speech_worker = SpeechWorker(self)

        self.speech_worker.status_changed.connect(
            self.voice_panel.set_status
        )
        self.speech_worker.transcript_ready.connect(
            self.handle_transcription
        )
        self.speech_worker.error_occurred.connect(
            self.handle_speech_error
        )
        self.speech_worker.finished.connect(
            self.speech_worker_finished
        )

        self.speech_worker.start()

    def handle_stop_requested(self):
        """Request the active recording to stop."""

        worker = self.speech_worker

        if worker is not None and worker.isRunning():
            self.voice_panel.stop_button.setEnabled(False)
            self.voice_panel.set_status(
                "Stopping recording and preparing transcription..."
            )
            self.status.setText("● Transcribing")

            worker.stop_recording()

        else:
            self.voice_panel.reset()
            self.status.setText("● Ready")

    def handle_transcription(self, text):
        """Display recognized speech and handle voice commands."""

        self.voice_panel.set_transcript(text)

        if (
            text.startswith("No speech detected")
            or text.startswith("No audio recorded")
        ):
            self.status.setText("● Ready")
            return

        self.add_message("You", text)

        # Normalize the recognized command.
        command = text.lower().strip().rstrip(".!?")
        words = command.split()

        # Common phrases that indicate the user does not want
        # Notepad opened.
        negative_phrases = [
            "close",
            "quit",
            "exit",
            "stop",
            "cancel",
            "don't",
            "dont",
            "do not",
            "never",
        ]

        is_negative = any(
            phrase in command
            for phrase in negative_phrases
        )

        # Accept "Open Notepad" and short transcription variations
        # such as "Robin Notepad".
        is_notepad_command = (
            "notepad" in words
            and len(words) <= 4
            and not is_negative
        )

        if is_notepad_command:
            try:
                subprocess.Popen(["notepad.exe"])

                self.status.setText("● Command executed")
                self.add_message(
                    "NavaAI",
                    "Opening Notepad."
                )

            except Exception as error:
                self.status.setText("● Error")
                self.add_message(
                    "NavaAI",
                    f"Could not open Notepad: {error}"
                )

        else:
            self.status.setText("● Speech recognized")

            self.add_message(
                "NavaAI",
                f"I heard: {text}. "
                "I don't have an action configured for this "
                "command yet."
            )

    def handle_speech_error(self, error):
        """Display microphone or transcription errors."""

        self.voice_panel.set_status("Speech recognition error")
        self.voice_panel.set_transcript(error)
        self.status.setText("● Error")

    def speech_worker_finished(self):
        """Restore controls after recording/transcription ends."""

        self.voice_panel.listen_button.setEnabled(True)
        self.voice_panel.stop_button.setEnabled(False)

        if self.status.text() != "● Error":
            self.status.setText("● Ready")

        self.voice_panel.set_status("Ready to listen")

    def clear_chat(self):
        """Clear chat messages and start a new conversation."""

        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)

            if item.widget() is not None:
                item.widget().deleteLater()

            elif item.layout() is not None:
                child_layout = item.layout()

                while child_layout.count():
                    child = child_layout.takeAt(0)

                    if child.widget() is not None:
                        child.widget().deleteLater()

        self.add_message(
            "NavaAI",
            "New conversation started. What should I do?"
        )

        self.status.setText("● Ready")
        self.voice_panel.reset()