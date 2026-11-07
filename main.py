import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from workbench_ui import STYLE, NavaAIWindow


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName('NavaAI')
    app.setApplicationName('Workbench')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)

    socket = QLocalSocket()
    socket.connectToServer('NavaAI.FYP.Workbench')
    if socket.waitForConnected(300):
        socket.disconnectFromServer()
        return
    server = QLocalServer()
    if not server.listen('NavaAI.FYP.Workbench'):
        return

    window = NavaAIWindow()
    window.show()

    def reveal():
        while server.hasPendingConnections():
            connection = server.nextPendingConnection()
            connection.disconnectFromServer()
            connection.deleteLater()
        if not window.busy:
            window.showNormal()
            window.raise_()
            window.activateWindow()
    server.newConnection.connect(reveal)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
