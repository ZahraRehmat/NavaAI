import sys

from PySide6.QtWidgets import QApplication
from navaai_ui import STYLE, NavaAIWindow


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    window = NavaAIWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()