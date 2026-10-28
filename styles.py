
APP_STYLE = """
QMainWindow, QWidget {
    background-color: #111116;
    color: #F1F0F6;
    font-family: 'Segoe UI';
    font-size: 14px;
}

QFrame#Sidebar {
    background-color: #191820;
    border-right: 1px solid #302D3A;
}

QLabel#Logo {
    color: #C4B5FD;
    font-size: 27px;
    font-weight: bold;
}

QLabel#Muted {
    color: #A5A1B5;
}

QLabel#PageTitle {
    font-size: 21px;
    font-weight: bold;
}

QLabel#Status {
    color: #C4B5FD;
    background-color: #292238;
    border: 1px solid #493968;
    border-radius: 10px;
    padding: 7px 12px;
}

QPushButton {
    background-color: #24222D;
    color: #F1F0F6;
    border: 1px solid #383544;
    border-radius: 9px;
    padding: 10px;
    text-align: left;
}

QPushButton:hover {
    background-color: #353044;
}

QPushButton#SendButton {
    background-color: #8B5CF6;
    color: white;
    border: none;
    font-weight: bold;
    padding: 12px 20px;
}

QPushButton#SendButton:hover {
    background-color: #7545D5;
}

QLineEdit {
    background-color: #1C1B24;
    border: 1px solid #3A3749;
    border-radius: 11px;
    padding: 13px;
    color: #FFFFFF;
}

QLineEdit:focus {
    border: 1px solid #8B5CF6;
}

QScrollArea {
    border: none;
}

QLabel#Message {
    background-color: #24222D;
    border: 1px solid #353242;
    border-radius: 10px;
    padding: 12px;
}
"""
