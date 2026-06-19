APP_STYLESHEET = """
QMainWindow {
    background: #121212;
    color: #e0e0e0;
}
QWidget {
    background: #121212;
    color: #e0e0e0;
    font-family: 'Segoe UI';
    font-size: 13px;
}
QFrame#sidebar {
    background: #1e1e1e;
    border-right: 1px solid #333333;
}
QLabel#h1 {
    font-size: 24px;
    font-weight: 700;
    color: #ffffff;
}
QLabel#muted {
    color: #aaaaaa;
}
QPushButton {
    background: #2d2d2d;
    color: white;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 8px 12px;
}
QPushButton:hover {
    background: #383838;
}
QPushButton#primary {
    background: #1976d2;
    border: none;
    font-weight: 700;
}
QPushButton#sidebar_btn {
    text-align: left;
    background: transparent;
    border: none;
    padding: 10px 12px;
}
QPushButton#sidebar_btn:hover {
    background: #2b2b2b;
    border-radius: 6px;
}
QPushButton#sidebar_btn:checked {
    background: #1976d2;
    border-radius: 6px;
    font-weight: 700;
}
QLineEdit, QComboBox, QTableView {
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 6px;
}
QHeaderView::section {
    background: #2d2d2d;
    color: white;
    border: none;
    padding: 8px;
}
QProgressBar {
    background: #1e1e1e;
    border: 1px solid #444;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk {
    background: #1976d2;
}
"""