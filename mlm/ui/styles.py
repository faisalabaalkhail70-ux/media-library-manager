"""Application stylesheets — dark glassmorphism and light themes.

Dark design tokens
──────────────────
  BG             #08080f   deep space
  BG-2           #0e0c1a   raised surface
  SIDEBAR        #0a0818   icon rail
  GLASS-04       rgba(255,255,255,0.04)
  GLASS-07       rgba(255,255,255,0.07)
  GLASS-10       rgba(255,255,255,0.10)
  BORDER         rgba(255,255,255,0.08)
  BORDER-HI      rgba(255,255,255,0.16)
  ACCENT         #7c6fff
  ACCENT-DIM     rgba(124,111,255,0.20)
  TEXT-HI        #f0f0ff
  TEXT-MID       #c4c4d8
  TEXT-MUTED     #606078
"""

DARK_STYLESHEET = """

/* ── Reset & base ──────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background: #08080f;
    color: #c4c4d8;
}
QWidget {
    background: #08080f;
    color: #c4c4d8;
    font-family: 'Segoe UI', 'Inter', system-ui, sans-serif;
    font-size: 13px;
}
QScrollArea,
QScrollArea > QWidget > QWidget { background: transparent; }

/* ── Custom title bar ──────────────────────────────────────────────── */
QWidget#title_bar {
    background: #0a0818;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
QLabel#title_bar_label {
    color: rgba(255,255,255,0.45);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: transparent;
}
/* Window control buttons */
QPushButton#wc_min, QPushButton#wc_max, QPushButton#wc_close {
    background: rgba(255,255,255,0.05);
    border: none;
    border-radius: 6px;
    color: rgba(255,255,255,0.40);
    font-size: 13px;
    font-weight: 400;
}
QPushButton#wc_min:hover  { background: rgba(255,255,255,0.10); color: #c4c4d8; }
QPushButton#wc_max:hover  { background: rgba(255,255,255,0.10); color: #c4c4d8; }
QPushButton#wc_close:hover { background: rgba(220,50,50,0.70); color: #ffffff; }

/* ── Icon sidebar ──────────────────────────────────────────────────── */
QFrame#sidebar {
    background: #0a0818;
    border-right: 1px solid rgba(255,255,255,0.06);
}
QLabel#sidebar_logo {
    color: #7c6fff;
    font-size: 22px;
    background: transparent;
}
QFrame#sidebar_divider {
    background: rgba(255,255,255,0.07);
    border: none;
    max-height: 1px;
}
QPushButton#sidebar_btn {
    background: transparent;
    border: none;
    border-radius: 12px;
    color: rgba(255,255,255,0.28);
    font-size: 20px;
    padding: 0;
}
QPushButton#sidebar_btn:hover {
    background: rgba(124,111,255,0.12);
    color: rgba(255,255,255,0.70);
}
QPushButton#sidebar_btn:checked {
    background: rgba(124,111,255,0.22);
    color: #7c6fff;
}
QToolTip {
    background: #12101e;
    color: #d0d0f8;
    border: 1px solid rgba(124,111,255,0.30);
    border-radius: 7px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 500;
}

/* ── Top bar ───────────────────────────────────────────────────────── */
QWidget#top_bar {
    background: #08080f;
    border: none;
}
QFrame#top_separator {
    background: rgba(255,255,255,0.05);
    border: none;
    max-height: 1px;
}

/* ── Content wrapper ───────────────────────────────────────────────── */
QWidget#content_wrapper, QWidget#right_panel {
    background: transparent;
}

/* ── Status bar ────────────────────────────────────────────────────── */
QFrame#status_bar {
    background: #0a0818;
    border-top: 1px solid rgba(255,255,255,0.05);
}
QLabel#status_label {
    color: #404058;
    font-size: 11px;
    background: transparent;
}

/* ── Glass cards ───────────────────────────────────────────────────── */
QFrame#card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
}
QFrame#stat_card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
}
QFrame#stat_card:hover {
    background: rgba(124,111,255,0.07);
    border-color: rgba(124,111,255,0.28);
}

/* ── Typography ────────────────────────────────────────────────────── */
QLabel#h1 {
    font-size: 21px;
    font-weight: 700;
    color: #f0f0ff;
    letter-spacing: -0.3px;
    background: transparent;
}
QLabel#h2 {
    font-size: 14px;
    font-weight: 600;
    color: #d0d0f0;
    background: transparent;
}
QLabel#muted {
    color: #505068;
    font-size: 11px;
    background: transparent;
}
QLabel#alert_banner {
    background: rgba(220,38,38,0.14);
    color: #fca5a5;
    border: 1px solid rgba(220,38,38,0.28);
    border-radius: 0;
    padding: 6px 16px;
    font-weight: 600;
    font-size: 12px;
}

/* ── Buttons ───────────────────────────────────────────────────────── */
QPushButton {
    background: rgba(255,255,255,0.06);
    color: #c4c4d8;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 9px;
    padding: 7px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background: rgba(255,255,255,0.10);
    border-color: rgba(255,255,255,0.16);
    color: #f0f0ff;
}
QPushButton:pressed {
    background: rgba(124,111,255,0.16);
    border-color: rgba(124,111,255,0.35);
}
QPushButton:disabled {
    background: rgba(255,255,255,0.02);
    color: #2a2a3a;
    border-color: rgba(255,255,255,0.04);
}
QPushButton#primary {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c6fff, stop:1 #5a50e0
    );
    color: #ffffff;
    border: 1px solid rgba(124,111,255,0.45);
    font-weight: 700;
}
QPushButton#primary:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #9484ff, stop:1 #6f64f0
    );
    border-color: rgba(148,132,255,0.65);
}
QPushButton#primary:pressed { background: #5040d0; }

/* ── Inputs ────────────────────────────────────────────────────────── */
QLineEdit, QComboBox {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 9px;
    padding: 7px 12px;
    color: #e0e0f8;
    selection-background-color: #7c6fff;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #7c6fff;
    background: rgba(124,111,255,0.07);
}
QLineEdit:hover, QComboBox:hover {
    border-color: rgba(255,255,255,0.16);
}
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #7c6fff;
    width: 0; height: 0;
}
QComboBox QAbstractItemView {
    background: #10101e;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 9px;
    selection-background-color: rgba(124,111,255,0.22);
    color: #c4c4d8;
    outline: none;
    padding: 4px;
}
QPlainTextEdit {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 8px;
    color: #e0e0f8;
    selection-background-color: #7c6fff;
}
QPlainTextEdit:focus { border-color: #7c6fff; }

/* ── Tables ────────────────────────────────────────────────────────── */
QTableView, QTableWidget {
    background: transparent;
    border: none;
    gridline-color: rgba(255,255,255,0.03);
    alternate-background-color: rgba(255,255,255,0.015);
    selection-background-color: rgba(124,111,255,0.18);
    selection-color: #f0f0ff;
    outline: none;
    border-radius: 0;
}
QTableView::item {
    padding: 5px 10px;
    border: none;
    color: #b8b8d0;
    border-bottom: 1px solid rgba(255,255,255,0.025);
}
QTableView::item:selected {
    background: rgba(124,111,255,0.18);
    color: #f0f0ff;
}
QTableView::item:hover:!selected {
    background: rgba(255,255,255,0.03);
}
QHeaderView {
    background: transparent;
    border: none;
}
QHeaderView::section {
    background: rgba(255,255,255,0.04);
    color: #5a5a80;
    border: none;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    border-right: 1px solid rgba(255,255,255,0.03);
    padding: 8px 10px;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}
QHeaderView::section:hover {
    background: rgba(124,111,255,0.08);
    color: #8888b8;
}
QHeaderView::section:checked {
    color: #7c6fff;
}
QHeaderView::section:first { border-top-left-radius: 0; }
QHeaderView::section:last  { border-right: none; }

/* ── List widget ───────────────────────────────────────────────────── */
QListWidget {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    outline: none;
}
QListWidget::item {
    padding: 7px 12px;
    border-radius: 7px;
    color: #b8b8d0;
}
QListWidget::item:hover  { background: rgba(255,255,255,0.04); }
QListWidget::item:selected { background: rgba(124,111,255,0.20); color: #f0f0ff; }

/* ── Progress bar ──────────────────────────────────────────────────── */
QProgressBar {
    background: rgba(255,255,255,0.05);
    border: none;
    border-radius: 4px;
    text-align: center;
    color: transparent;
    height: 4px;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c6fff, stop:1 #a78bfa
    );
    border-radius: 4px;
}

/* ── Group boxes ───────────────────────────────────────────────────── */
QGroupBox {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    margin-top: 16px;
    padding-top: 10px;
    font-weight: 600;
    color: #b0b0c8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    color: #6060a0;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}

/* ── CheckBox & RadioButton ────────────────────────────────────────── */
QCheckBox, QRadioButton { color: #b8b8d0; spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px; height: 15px;
    border: 1px solid rgba(255,255,255,0.16);
    border-radius: 4px;
    background: rgba(255,255,255,0.04);
}
QCheckBox::indicator:checked  { background: #7c6fff; border-color: #7c6fff; }
QCheckBox::indicator:hover     { border-color: #7c6fff; }
QRadioButton::indicator        { border-radius: 8px; }
QRadioButton::indicator:checked { background: #7c6fff; border-color: #7c6fff; }

/* ── Scrollbars ────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent; width: 5px; margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.10);
    border-radius: 3px; min-height: 30px;
}
QScrollBar::handle:vertical:hover { background: rgba(124,111,255,0.45); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 5px; margin: 0; }
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.10);
    border-radius: 3px; min-width: 30px;
}
QScrollBar::handle:horizontal:hover { background: rgba(124,111,255,0.45); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }

/* ── Poster card ───────────────────────────────────────────────────── */
QFrame#poster_card {
    background: transparent;
    border: none;
}

/* ── Dialogs & message boxes ───────────────────────────────────────── */
QMessageBox { background: #0e0c1a; }
QMessageBox QLabel { color: #c4c4d8; }
QMessageBox QPushButton { min-width: 88px; padding: 7px 20px; }

/* ── Tab widget ────────────────────────────────────────────────────── */
QTabWidget::pane {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background: rgba(255,255,255,0.03);
    color: #505068;
    border: 1px solid rgba(255,255,255,0.06);
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    padding: 6px 18px;
    margin-right: 2px;
    font-weight: 500;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: rgba(124,111,255,0.16);
    color: #f0f0ff;
    border-color: rgba(124,111,255,0.28);
    font-weight: 700;
}
QTabBar::tab:hover { background: rgba(255,255,255,0.06); color: #a0a0c0; }

/* ── Splitter ──────────────────────────────────────────────────────── */
QSplitter::handle { background: rgba(255,255,255,0.05); width: 1px; }
QSplitter::handle:hover { background: #7c6fff; }

/* ── Separator lines ───────────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.06);
    border: none;
    max-height: 1px;
}

/* ── Context / popup menus ─────────────────────────────────────────── */
QMenu {
    background: #10101e;
    border: 1px solid rgba(124,111,255,0.18);
    border-radius: 11px;
    padding: 5px;
    color: #c4c4d8;
}
QMenu::item {
    padding: 7px 30px 7px 14px;
    border-radius: 7px;
    font-size: 13px;
}
QMenu::item:selected { background: rgba(124,111,255,0.18); color: #f0f0ff; }
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.06);
    margin: 4px 10px;
}

"""

# ── LIGHT ───────────────────────────────────────────────────────────────────
LIGHT_STYLESHEET = """

QMainWindow, QDialog { background: #f2f2f8; color: #18182a; }
QWidget {
    background: #f2f2f8;
    color: #18182a;
    font-family: 'Segoe UI', 'Inter', system-ui, sans-serif;
    font-size: 13px;
}
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }

QWidget#title_bar {
    background: rgba(255,255,255,0.90);
    border-bottom: 1px solid rgba(0,0,0,0.07);
}
QLabel#title_bar_label {
    color: rgba(0,0,0,0.35); font-size: 12px;
    font-weight: 600; letter-spacing: 0.5px; background: transparent;
}
QPushButton#wc_min, QPushButton#wc_max {
    background: rgba(0,0,0,0.04); border: none; border-radius: 6px;
    color: rgba(0,0,0,0.35); font-size: 13px;
}
QPushButton#wc_min:hover, QPushButton#wc_max:hover {
    background: rgba(0,0,0,0.08); color: #18182a;
}
QPushButton#wc_close { background: rgba(0,0,0,0.04); border: none; border-radius: 6px; color: rgba(0,0,0,0.35); font-size: 13px; }
QPushButton#wc_close:hover { background: rgba(220,50,50,0.80); color: #ffffff; }

QFrame#sidebar { background: #eaeaf4; border-right: 1px solid rgba(0,0,0,0.06); }
QLabel#sidebar_logo { color: #7c6fff; font-size: 22px; background: transparent; }
QFrame#sidebar_divider { background: rgba(0,0,0,0.07); border: none; max-height: 1px; }
QPushButton#sidebar_btn {
    background: transparent; border: none; border-radius: 12px;
    color: rgba(0,0,0,0.28); font-size: 20px; padding: 0;
}
QPushButton#sidebar_btn:hover { background: rgba(124,111,255,0.10); color: rgba(0,0,0,0.65); }
QPushButton#sidebar_btn:checked { background: rgba(124,111,255,0.18); color: #7c6fff; }
QToolTip {
    background: #ffffff; color: #18182a;
    border: 1px solid rgba(124,111,255,0.25);
    border-radius: 7px; padding: 5px 12px; font-size: 12px;
}

QWidget#top_bar { background: #f2f2f8; border: none; }
QFrame#top_separator { background: rgba(0,0,0,0.06); border: none; max-height: 1px; }
QWidget#content_wrapper, QWidget#right_panel { background: transparent; }
QFrame#status_bar { background: #eaeaf4; border-top: 1px solid rgba(0,0,0,0.06); }
QLabel#status_label { color: #9090b0; font-size: 11px; background: transparent; }

QFrame#card { background: rgba(255,255,255,0.80); border: 1px solid rgba(0,0,0,0.07); border-radius: 16px; }
QFrame#stat_card { background: rgba(255,255,255,0.90); border: 1px solid rgba(0,0,0,0.07); border-radius: 16px; }
QFrame#stat_card:hover { border-color: rgba(124,111,255,0.35); background: rgba(124,111,255,0.04); }

QLabel#h1 { font-size: 21px; font-weight: 700; color: #0c0c20; letter-spacing: -0.3px; background: transparent; }
QLabel#h2 { font-size: 14px; font-weight: 600; color: #28283a; background: transparent; }
QLabel#muted { color: #9090b0; font-size: 11px; background: transparent; }
QLabel#alert_banner { background: rgba(220,38,38,0.10); color: #b91c1c; border: 1px solid rgba(220,38,38,0.22); border-radius: 0; padding: 6px 16px; font-weight: 600; font-size: 12px; }

QPushButton { background: rgba(255,255,255,0.90); color: #28283a; border: 1px solid rgba(0,0,0,0.11); border-radius: 9px; padding: 7px 16px; font-size: 13px; font-weight: 500; }
QPushButton:hover { background: #ffffff; border-color: rgba(124,111,255,0.38); color: #0c0c20; }
QPushButton:pressed { background: rgba(124,111,255,0.09); }
QPushButton:disabled { background: #efefef; color: #b0b0c8; border-color: rgba(0,0,0,0.06); }
QPushButton#primary { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c6fff,stop:1 #5a50e0); color: #fff; border: none; font-weight: 700; }
QPushButton#primary:hover { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #9484ff,stop:1 #6f64f0); }

QLineEdit, QComboBox { background: rgba(255,255,255,0.95); border: 1px solid rgba(0,0,0,0.12); border-radius: 9px; padding: 7px 12px; color: #18182a; selection-background-color: #7c6fff; }
QLineEdit:focus, QComboBox:focus { border-color: #7c6fff; }
QPlainTextEdit { background: #ffffff; border: 1px solid rgba(0,0,0,0.10); border-radius: 10px; padding: 8px; color: #18182a; }
QPlainTextEdit:focus { border-color: #7c6fff; }

QTableView, QTableWidget { background: transparent; border: none; gridline-color: rgba(0,0,0,0.04); alternate-background-color: rgba(0,0,0,0.015); selection-background-color: rgba(124,111,255,0.12); selection-color: #0c0c20; outline: none; }
QTableView::item { padding: 5px 10px; border: none; color: #38384a; border-bottom: 1px solid rgba(0,0,0,0.04); }
QTableView::item:selected { background: rgba(124,111,255,0.12); color: #0c0c20; }
QTableView::item:hover:!selected { background: rgba(0,0,0,0.02); }
QHeaderView::section { background: rgba(0,0,0,0.03); color: #8080a8; border: none; border-bottom: 1px solid rgba(0,0,0,0.06); padding: 8px 10px; font-weight: 700; font-size: 10px; letter-spacing: 0.8px; }
QHeaderView::section:hover { background: rgba(124,111,255,0.06); color: #5050a0; }

QListWidget { background: rgba(255,255,255,0.80); border: 1px solid rgba(0,0,0,0.07); border-radius: 10px; outline: none; }
QListWidget::item { padding: 7px 12px; border-radius: 7px; color: #38384a; }
QListWidget::item:selected { background: rgba(124,111,255,0.14); color: #0c0c20; }

QProgressBar { background: rgba(0,0,0,0.07); border: none; border-radius: 4px; height: 4px; }
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c6fff,stop:1 #a78bfa); border-radius: 4px; }

QGroupBox { background: rgba(255,255,255,0.70); border: 1px solid rgba(0,0,0,0.07); border-radius: 12px; margin-top: 16px; padding-top: 10px; font-weight: 600; color: #38384a; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px; color: #7c6fff; font-size: 10px; font-weight: 700; letter-spacing: 0.8px; }

QCheckBox, QRadioButton { color: #38384a; spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator { width: 15px; height: 15px; border: 1px solid rgba(0,0,0,0.18); border-radius: 4px; background: rgba(255,255,255,0.90); }
QCheckBox::indicator:checked { background: #7c6fff; border-color: #7c6fff; }
QRadioButton::indicator { border-radius: 8px; }
QRadioButton::indicator:checked { background: #7c6fff; border-color: #7c6fff; }

QScrollBar:vertical { background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: rgba(0,0,0,0.12); border-radius: 3px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: rgba(124,111,255,0.50); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 5px; }
QScrollBar::handle:horizontal { background: rgba(0,0,0,0.12); border-radius: 3px; min-width: 30px; }
QScrollBar::handle:horizontal:hover { background: rgba(124,111,255,0.50); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QFrame#poster_card { background: transparent; border: none; }
QMessageBox { background: #f8f8fc; }
QMessageBox QLabel { color: #18182a; }
QMessageBox QPushButton { min-width: 88px; padding: 7px 20px; }
QMenu { background: rgba(255,255,255,0.97); border: 1px solid rgba(124,111,255,0.14); border-radius: 11px; padding: 5px; color: #18182a; }
QMenu::item { padding: 7px 30px 7px 14px; border-radius: 7px; font-size: 13px; }
QMenu::item:selected { background: rgba(124,111,255,0.10); color: #0c0c20; }
QMenu::separator { height: 1px; background: rgba(0,0,0,0.06); margin: 4px 10px; }
"""

# Back-compat alias
APP_STYLESHEET = DARK_STYLESHEET


def get_stylesheet(theme: str) -> str:
    return LIGHT_STYLESHEET if theme == "light" else DARK_STYLESHEET
