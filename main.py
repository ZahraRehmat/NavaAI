import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from workbench_ui import STYLE, NavaAIWindow

SERVER_NAME = 'NavaAI.FYP.Workbench.voice'


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName('NavaAI')
    app.setApplicationName('Workbench')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)

    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(300):
        socket.disconnectFromServer()
        return
    server = QLocalServer()
    if not server.listen(SERVER_NAME):
        QLocalServer.removeServer(SERVER_NAME)
        if not server.listen(SERVER_NAME):
            return

    # The regular launcher opens the compact local-voice panel. The full
    # Gwen-connected workbench remains available with --workbench.
    window = NavaAIWindow(connect='--workbench' in sys.argv)
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
