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
QScrollArea, QScrollArea > QWidget > QWidget {
    background: #121212;
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
QLabel#h2 {
    font-size: 16px;
    font-weight: 700;
    color: #eeeeee;
}
QLabel#muted {
    color: #aaaaaa;
}
QFrame#stat_card {
    background: #1e1e1e;
    border: 1px solid #2c2c2c;
    border-radius: 10px;
}
QPushButton {
    background: #2d2d2d;
    color: white;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton:hover {
    background: #383838;
    border-color: #555;
}
QPushButton:disabled {
    background: #252525;
    color: #555555;
}
QPushButton#primary {
    background: #1976d2;
    border: none;
    font-weight: 700;
}
QPushButton#primary:hover {
    background: #1e88e5;
}
QPushButton#sidebar_btn {
    text-align: left;
    background: transparent;
    border: none;
    padding: 10px 12px;
    border-radius: 6px;
}
QPushButton#sidebar_btn:hover {
    background: #2b2b2b;
}
QPushButton#sidebar_btn:checked {
    background: #1976d2;
    font-weight: 700;
}
QLineEdit, QComboBox {
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e0e0e0;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #1976d2;
}
QPlainTextEdit {
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 6px;
    color: #e0e0e0;
}
QTableView, QTableWidget {
    background: #1e1e1e;
    border: 1px solid #2c2c2c;
    border-radius: 6px;
    gridline-color: #2a2a2a;
    alternate-background-color: #1a1a1a;
    selection-background-color: #1976d2;
    selection-color: white;
}
QHeaderView::section {
    background: #252525;
    color: #cccccc;
    border: none;
    border-bottom: 1px solid #333;
    padding: 8px;
    font-weight: 600;
}
QGroupBox {
    border: 1px solid #2c2c2c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 8px;
    font-weight: 600;
    color: #cccccc;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #ffffff;
}
QProgressBar {
    background: #1e1e1e;
    border: 1px solid #333;
    border-radius: 5px;
    text-align: center;
    color: white;
    height: 12px;
}
QProgressBar::chunk {
    background: #1976d2;
    border-radius: 5px;
}
QListWidget {
    background: #1e1e1e;
    border: 1px solid #2c2c2c;
    border-radius: 6px;
    alternate-background-color: #1a1a1a;
}
QListWidget::item:selected {
    background: #1976d2;
    color: white;
}
QScrollBar:vertical {
    background: #1a1a1a;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #3a3a3a;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #4a4a4a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QMessageBox {
    background: #1e1e1e;
}
"""