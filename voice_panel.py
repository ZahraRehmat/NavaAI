from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class VoicePanel(QFrame):
    listen_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("VoicePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        title = QLabel("Voice Assistant")
        title.setStyleSheet(
            "font-size: 17px; font-weight: bold;"
        )

        self.status_label = QLabel("Ready to listen")
        self.status_label.setObjectName("Muted")

        self.transcript_label = QLabel(
            "Your recognized speech will appear here."
        )
        self.transcript_label.setWordWrap(True)
        self.transcript_label.setMinimumHeight(45)
        self.transcript_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        buttons = QHBoxLayout()

        self.listen_button = QPushButton("🎙 Start listening")
        self.listen_button.setObjectName("SendButton")
        self.listen_button.clicked.connect(
            self.request_listening
        )

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(
            self.stop_requested.emit
        )

        buttons.addWidget(self.listen_button)
        buttons.addWidget(self.stop_button)

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.transcript_label)
        layout.addLayout(buttons)

    def request_listening(self):
        print("DEBUG: Start Listening button clicked!")

        self.status_label.setText("Listening requested...")
        self.listen_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        print("DEBUG: Sending listening request to main window")
        self.listen_requested.emit()

    def set_transcript(self, text):
        self.transcript_label.setText(text)

    def set_status(self, text):
        self.status_label.setText(text)

    def reset(self):
        self.status_label.setText("Ready to listen")
        self.listen_button.setEnabled(True)
        self.stop_button.setEnabled(False)