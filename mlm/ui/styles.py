"""Application stylesheets — dark glassmorphism (default) and light themes.

Dark theme design language (2026 Glassmorphism)
  ───────────────────────────────────────
  Background  : #08080f  (deep space navy, near black)
  Surface L1  : rgba(255,255,255,0.04)  (frosted card base)
  Surface L2  : rgba(255,255,255,0.07)  (elevated panels, sidebar)
  Surface L3  : rgba(255,255,255,0.10)  (inputs, header sections)
  Border      : rgba(255,255,255,0.09)  (1px frosted rim)
  Border hi   : rgba(255,255,255,0.16)  (hover / active rim)
  Accent      : #7c6fff  (violet-purple)
  Accent glow : #6c63ff  (slightly deeper for shadows)
  Text hi     : #f0f0ff
  Text mid    : #c8c8d8
  Text muted  : #72728a
"""

# ─────────────────────────────────────────────────────────────────────────────
# DARK  —  Glassmorphism / Spatial Dark
# ─────────────────────────────────────────────────────────────────────────────
DARK_STYLESHEET = """

/* ──── Base ────────────────────────────────────────────────────── */
QMainWindow, QDialog {
    background: #08080f;
    color: #c8c8d8;
}
QWidget {
    background: #08080f;
    color: #c8c8d8;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}
QScrollArea,
QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* ──── Sidebar ─────────────────────────────────────────────── */
QFrame#sidebar {
    background: rgba(16, 14, 30, 0.95);
    border-right: 1px solid rgba(255,255,255,0.07);
}

/* ──── Sidebar nav buttons ──────────────────────────────────── */
QPushButton#sidebar_btn {
    text-align: left;
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    color: #8888a8;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#sidebar_btn:hover {
    background: rgba(124,111,255,0.10);
    color: #d0d0f0;
}
QPushButton#sidebar_btn:checked {
    background: rgba(124,111,255,0.20);
    color: #ffffff;
    font-weight: 700;
    border-left: 3px solid #7c6fff;
    padding-left: 11px;
}

/* ──── Glass cards (QFrame#card, QFrame#stat_card) ────────────── */
QFrame#card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
}
QFrame#stat_card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 14px;
}
QFrame#stat_card:hover {
    background: rgba(124,111,255,0.08);
    border-color: rgba(124,111,255,0.30);
}

/* ──── Typography ────────────────────────────────────────────── */
QLabel#h1 {
    font-size: 22px;
    font-weight: 700;
    color: #f0f0ff;
    letter-spacing: 0.3px;
}
QLabel#h2 {
    font-size: 15px;
    font-weight: 600;
    color: #d8d8f0;
}
QLabel#muted {
    color: #72728a;
    font-size: 12px;
}
QLabel#alert_banner {
    background: rgba(220, 38, 38, 0.18);
    color: #fca5a5;
    border: 1px solid rgba(220,38,38,0.35);
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}

/* ──── Buttons ──────────────────────────────────────────────── */
QPushButton {
    background: rgba(255,255,255,0.07);
    color: #d0d0f0;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background: rgba(255,255,255,0.12);
    border-color: rgba(255,255,255,0.18);
    color: #ffffff;
}
QPushButton:pressed {
    background: rgba(124,111,255,0.18);
    border-color: rgba(124,111,255,0.40);
}
QPushButton:disabled {
    background: rgba(255,255,255,0.03);
    color: #3a3a50;
    border-color: rgba(255,255,255,0.04);
}
QPushButton#primary {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c6fff,
        stop:1 #5a50e0
    );
    color: #ffffff;
    border: 1px solid rgba(124,111,255,0.50);
    font-weight: 700;
}
QPushButton#primary:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #9484ff,
        stop:1 #6f64f0
    );
    border-color: rgba(148,132,255,0.70);
}
QPushButton#primary:pressed {
    background: #5a50e0;
}

/* ──── Inputs ───────────────────────────────────────────────── */
QLineEdit,
QComboBox {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 8px;
    padding: 7px 12px;
    color: #e0e0f8;
    selection-background-color: #7c6fff;
}
QLineEdit:focus,
QComboBox:focus {
    border-color: #7c6fff;
    background: rgba(124,111,255,0.08);
}
QLineEdit:hover,
QComboBox:hover {
    border-color: rgba(255,255,255,0.18);
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #7c6fff;
    width: 0;
    height: 0;
}
QComboBox QAbstractItemView {
    background: #12101e;
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 8px;
    selection-background-color: rgba(124,111,255,0.25);
    color: #c8c8d8;
    outline: none;
}
QPlainTextEdit {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 10px;
    padding: 8px;
    color: #e0e0f8;
    selection-background-color: #7c6fff;
}
QPlainTextEdit:focus {
    border-color: #7c6fff;
}

/* ──── Tables ───────────────────────────────────────────────── */
QTableView,
QTableWidget {
    background: transparent;
    border: none;
    gridline-color: rgba(255,255,255,0.04);
    alternate-background-color: rgba(255,255,255,0.02);
    selection-background-color: rgba(124,111,255,0.22);
    selection-color: #f0f0ff;
    border-radius: 10px;
    outline: none;
}
QTableView::item {
    padding: 6px 8px;
    border: none;
    color: #c8c8d8;
}
QTableView::item:selected {
    background: rgba(124,111,255,0.22);
    color: #f0f0ff;
    border-left: 2px solid #7c6fff;
}
QTableView::item:hover {
    background: rgba(255,255,255,0.04);
}
QHeaderView {
    background: transparent;
}
QHeaderView::section {
    background: rgba(255,255,255,0.05);
    color: #7c6fff;
    border: none;
    border-bottom: 1px solid rgba(124,111,255,0.20);
    border-right: 1px solid rgba(255,255,255,0.04);
    padding: 9px 10px;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
QHeaderView::section:hover {
    background: rgba(124,111,255,0.10);
    color: #a89fff;
}
QHeaderView::section:first {
    border-top-left-radius: 10px;
}
QHeaderView::section:last {
    border-top-right-radius: 10px;
    border-right: none;
}

/* ──── List widget ───────────────────────────────────────────── */
QListWidget {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    outline: none;
    alternate-background-color: rgba(255,255,255,0.02);
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    color: #c8c8d8;
}
QListWidget::item:hover {
    background: rgba(255,255,255,0.05);
}
QListWidget::item:selected {
    background: rgba(124,111,255,0.22);
    color: #f0f0ff;
}

/* ──── Progress bars ─────────────────────────────────────────── */
QProgressBar {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 6px;
    text-align: center;
    color: #c8c8d8;
    height: 10px;
    font-size: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c6fff,
        stop:1 #a78bfa
    );
    border-radius: 6px;
}

/* ──── Group boxes ───────────────────────────────────────────── */
QGroupBox {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    margin-top: 14px;
    padding-top: 10px;
    font-weight: 600;
    color: #c8c8d8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 8px;
    color: #a89fff;
    font-size: 11px;
    letter-spacing: 0.5px;
}

/* ──── CheckBox & RadioButton ─────────────────────────────────── */
QCheckBox,
QRadioButton {
    color: #c8c8d8;
    spacing: 8px;
}
QCheckBox::indicator,
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 4px;
    background: rgba(255,255,255,0.05);
}
QCheckBox::indicator:checked {
    background: #7c6fff;
    border-color: #7c6fff;
}
QCheckBox::indicator:hover,
QRadioButton::indicator:hover {
    border-color: #7c6fff;
}
QRadioButton::indicator {
    border-radius: 8px;
}
QRadioButton::indicator:checked {
    background: #7c6fff;
    border-color: #7c6fff;
}

/* ──── Scrollbars ────────────────────────────────────────────── */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(124,111,255,0.25);
    border-radius: 3px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(124,111,255,0.50);
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical { background: transparent; }

QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: rgba(124,111,255,0.25);
    border-radius: 3px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(124,111,255,0.50);
}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal { background: transparent; }

/* ──── Poster card ───────────────────────────────────────────── */
QFrame#poster_card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
}
QFrame#poster_card:hover {
    background: rgba(124,111,255,0.09);
    border: 1px solid rgba(124,111,255,0.40);
}

/* ──── Dialogs & Message boxes ───────────────────────────────── */
QMessageBox {
    background: #0e0c1a;
}
QMessageBox QLabel {
    color: #c8c8d8;
}
QMessageBox QPushButton {
    min-width: 90px;
    padding: 7px 20px;
}

/* ──── ToolTip ───────────────────────────────────────────────── */
QToolTip {
    background: #12101e;
    color: #d0d0f0;
    border: 1px solid rgba(124,111,255,0.35);
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
}

/* ──── Tab widget (used in some views) ──────────────────────────── */
QTabWidget::pane {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background: rgba(255,255,255,0.04);
    color: #72728a;
    border: 1px solid rgba(255,255,255,0.07);
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    padding: 7px 18px;
    margin-right: 2px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: rgba(124,111,255,0.18);
    color: #f0f0ff;
    border-color: rgba(124,111,255,0.30);
    font-weight: 700;
}
QTabBar::tab:hover {
    background: rgba(255,255,255,0.07);
    color: #c8c8d8;
}

/* ──── Splitter ──────────────────────────────────────────────── */
QSplitter::handle {
    background: rgba(255,255,255,0.06);
    width: 1px;
}
QSplitter::handle:hover {
    background: #7c6fff;
}

/* ──── Separator lines ─────────────────────────────────────────── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {
    color: rgba(255,255,255,0.07);
    background: rgba(255,255,255,0.07);
    border: none;
    max-height: 1px;
}

/* ──── Context / popup menus ──────────────────────────────────── */
QMenu {
    background: #12101e;
    border: 1px solid rgba(124,111,255,0.20);
    border-radius: 10px;
    padding: 4px;
    color: #c8c8d8;
}
QMenu::item {
    padding: 7px 28px 7px 14px;
    border-radius: 6px;
    font-size: 13px;
}
QMenu::item:selected {
    background: rgba(124,111,255,0.20);
    color: #f0f0ff;
}
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.07);
    margin: 4px 10px;
}
QMenu::icon {
    padding-left: 10px;
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# LIGHT  —  Clean Frosted Light
# ─────────────────────────────────────────────────────────────────────────────
LIGHT_STYLESHEET = """

QMainWindow, QDialog { background: #f4f4f8; color: #1a1a2e; }
QWidget {
    background: #f4f4f8;
    color: #1a1a2e;
    font-family: 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }

QFrame#sidebar {
    background: rgba(255,255,255,0.80);
    border-right: 1px solid rgba(0,0,0,0.08);
}
QPushButton#sidebar_btn {
    text-align: left; background: transparent; border: none;
    border-radius: 8px; padding: 10px 14px;
    color: #555577; font-size: 13px; font-weight: 500;
}
QPushButton#sidebar_btn:hover { background: rgba(124,111,255,0.08); color: #2a2a4a; }
QPushButton#sidebar_btn:checked {
    background: rgba(124,111,255,0.14); color: #3a30cc;
    font-weight: 700; border-left: 3px solid #7c6fff; padding-left: 11px;
}

QFrame#card {
    background: rgba(255,255,255,0.80);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 14px;
}
QFrame#stat_card {
    background: rgba(255,255,255,0.90);
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 14px;
}
QFrame#stat_card:hover {
    border-color: rgba(124,111,255,0.40);
    background: rgba(124,111,255,0.05);
}

QLabel#h1 { font-size: 22px; font-weight: 700; color: #0e0e20; letter-spacing: 0.3px; }
QLabel#h2 { font-size: 15px; font-weight: 600; color: #2a2a3a; }
QLabel#muted { color: #8888aa; font-size: 12px; }
QLabel#alert_banner {
    background: rgba(220,38,38,0.10); color: #b91c1c;
    border: 1px solid rgba(220,38,38,0.25);
    border-radius: 8px; padding: 7px 14px; font-weight: 600; font-size: 12px;
}

QPushButton {
    background: rgba(255,255,255,0.90); color: #2a2a4a;
    border: 1px solid rgba(0,0,0,0.12);
    border-radius: 8px; padding: 8px 16px;
    font-size: 13px; font-weight: 500;
}
QPushButton:hover { background: #ffffff; border-color: rgba(124,111,255,0.40); color: #1a1a2e; }
QPushButton:pressed { background: rgba(124,111,255,0.10); border-color: rgba(124,111,255,0.50); }
QPushButton:disabled { background: #f0f0f4; color: #b0b0c4; border-color: rgba(0,0,0,0.06); }
QPushButton#primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c6fff,stop:1 #5a50e0);
    color: #ffffff; border: none; font-weight: 700;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #9484ff,stop:1 #6f64f0);
}

QLineEdit, QComboBox {
    background: rgba(255,255,255,0.95); border: 1px solid rgba(0,0,0,0.12);
    border-radius: 8px; padding: 7px 12px; color: #1a1a2e;
    selection-background-color: #7c6fff;
}
QLineEdit:focus, QComboBox:focus { border-color: #7c6fff; }
QPlainTextEdit {
    background: #ffffff; border: 1px solid rgba(0,0,0,0.10);
    border-radius: 10px; padding: 8px; color: #1a1a2e;
}
QPlainTextEdit:focus { border-color: #7c6fff; }

QTableView, QTableWidget {
    background: transparent; border: none;
    gridline-color: rgba(0,0,0,0.05);
    alternate-background-color: rgba(0,0,0,0.02);
    selection-background-color: rgba(124,111,255,0.15);
    selection-color: #1a1a2e; border-radius: 10px; outline: none;
}
QTableView::item { padding: 6px 8px; border: none; color: #2a2a3a; }
QTableView::item:selected { background: rgba(124,111,255,0.15); color: #0e0e20; border-left: 2px solid #7c6fff; }
QTableView::item:hover { background: rgba(0,0,0,0.03); }
QHeaderView::section {
    background: rgba(0,0,0,0.03); color: #7c6fff;
    border: none; border-bottom: 1px solid rgba(124,111,255,0.15);
    padding: 9px 10px; font-weight: 600; font-size: 11px; letter-spacing: 0.5px;
}
QHeaderView::section:hover { background: rgba(124,111,255,0.07); }

QListWidget {
    background: rgba(255,255,255,0.80); border: 1px solid rgba(0,0,0,0.08);
    border-radius: 10px; outline: none;
}
QListWidget::item { padding: 8px 12px; border-radius: 6px; color: #2a2a3a; }
QListWidget::item:selected { background: rgba(124,111,255,0.15); color: #0e0e20; }

QProgressBar {
    background: rgba(0,0,0,0.07); border: none; border-radius: 6px;
    text-align: center; color: #2a2a3a; height: 10px; font-size: 10px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c6fff,stop:1 #a78bfa);
    border-radius: 6px;
}

QGroupBox {
    background: rgba(255,255,255,0.70); border: 1px solid rgba(0,0,0,0.08);
    border-radius: 12px; margin-top: 14px; padding-top: 10px;
    font-weight: 600; color: #2a2a3a;
}
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 8px; color: #7c6fff; font-size: 11px; }

QCheckBox, QRadioButton { color: #2a2a3a; spacing: 8px; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 16px; height: 16px;
    border: 1px solid rgba(0,0,0,0.20); border-radius: 4px;
    background: rgba(255,255,255,0.90);
}
QCheckBox::indicator:checked { background: #7c6fff; border-color: #7c6fff; }
QRadioButton::indicator { border-radius: 8px; }
QRadioButton::indicator:checked { background: #7c6fff; border-color: #7c6fff; }

QScrollBar:vertical { background: transparent; width: 6px; }
QScrollBar::handle:vertical { background: rgba(124,111,255,0.25); border-radius: 3px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: rgba(124,111,255,0.50); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 6px; }
QScrollBar::handle:horizontal { background: rgba(124,111,255,0.25); border-radius: 3px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: rgba(124,111,255,0.50); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QFrame#poster_card {
    background: rgba(255,255,255,0.85); border: 1px solid rgba(0,0,0,0.08); border-radius: 12px;
}
QFrame#poster_card:hover {
    border-color: rgba(124,111,255,0.50); background: rgba(124,111,255,0.05);
}

QMessageBox { background: #f8f8fc; }
QMessageBox QLabel { color: #1a1a2e; }
QMessageBox QPushButton { min-width: 90px; padding: 7px 20px; }

QToolTip {
    background: #ffffff; color: #1a1a2e;
    border: 1px solid rgba(124,111,255,0.30);
    border-radius: 6px; padding: 5px 10px; font-size: 12px;
}

QMenu {
    background: rgba(255,255,255,0.97); border: 1px solid rgba(124,111,255,0.15);
    border-radius: 10px; padding: 4px; color: #1a1a2e;
}
QMenu::item { padding: 7px 28px 7px 14px; border-radius: 6px; font-size: 13px; }
QMenu::item:selected { background: rgba(124,111,255,0.12); color: #1a1a2e; }
QMenu::separator { height: 1px; background: rgba(0,0,0,0.07); margin: 4px 10px; }
"""

# Back-compat alias used by bootstrap.py
APP_STYLESHEET = DARK_STYLESHEET


def get_stylesheet(theme: str) -> str:
    """Return the stylesheet for *theme* ('dark' or 'light')."""
    return LIGHT_STYLESHEET if theme == "light" else DARK_STYLESHEET
