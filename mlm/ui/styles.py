"""Application stylesheets — dark deep-space and light frosted-glass themes.

Dark design tokens
──────────────────
  BG             #07070d   deep void
  BG-2           #0d0b1a   raised surface
  BG-3           #110f20   elevated card
  SIDEBAR        #090717   icon rail
  GLASS-03       rgba(255,255,255,0.03)
  GLASS-06       rgba(255,255,255,0.06)
  GLASS-10       rgba(255,255,255,0.10)
  BORDER         rgba(255,255,255,0.07)
  BORDER-HI      rgba(255,255,255,0.15)
  ACCENT         #7c6fff   violet
  ACCENT-2       #a78bfa   soft lavender
  ACCENT-3       #38bdf8   cyan highlight
  SUCCESS        #34d399   emerald
  WARN           #fbbf24   amber
  DANGER         #f87171   rose
  TEXT-HI        #f4f4ff
  TEXT-MID       #c0c0d8
  TEXT-MUTED     #50506a
  TEXT-DIM       #30303e
"""

DARK_STYLESHEET = """

/* ══════════════════════════════════════════════════════════════════════
   RESET & BASE
   ══════════════════════════════════════════════════════════════════════ */
QMainWindow, QDialog {
    background: #07070d;
    color: #c0c0d8;
}
QWidget {
    background: #07070d;
    color: #c0c0d8;
    font-family: 'Segoe UI', 'Inter', 'SF Pro Display', system-ui, sans-serif;
    font-size: 13px;
}
QScrollArea,
QScrollArea > QWidget > QWidget { background: transparent; }


/* ══════════════════════════════════════════════════════════════════════
   CUSTOM TITLE BAR
   ══════════════════════════════════════════════════════════════════════ */
QWidget#title_bar {
    background: #090717;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
QLabel#title_bar_label {
    color: rgba(255,255,255,0.30);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1.2px;
    background: transparent;
}
QPushButton#wc_min, QPushButton#wc_max, QPushButton#wc_close {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 6px;
    color: rgba(255,255,255,0.30);
    font-size: 12px;
}
QPushButton#wc_min:hover  { background: rgba(255,255,255,0.09); color: #c0c0d8; border-color: rgba(255,255,255,0.12); }
QPushButton#wc_max:hover  { background: rgba(255,255,255,0.09); color: #c0c0d8; border-color: rgba(255,255,255,0.12); }
QPushButton#wc_close:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #dc2626,stop:1 #b91c1c);
    border-color: rgba(220,38,38,0.60);
    color: #ffffff;
}


/* ══════════════════════════════════════════════════════════════════════
   ICON SIDEBAR
   ══════════════════════════════════════════════════════════════════════ */
QFrame#sidebar {
    background: qlineargradient(
        x1:0, y1:0, x2:0, y2:1,
        stop:0   #090717,
        stop:0.5 #0a0818,
        stop:1   #090717
    );
    border-right: 1px solid rgba(255,255,255,0.05);
}
QLabel#sidebar_logo {
    color: #7c6fff;
    font-size: 24px;
    background: transparent;
}
QFrame#sidebar_divider {
    background: rgba(255,255,255,0.06);
    border: none;
    max-height: 1px;
}
QPushButton#sidebar_btn {
    background: transparent;
    border: none;
    border-radius: 14px;
    color: rgba(255,255,255,0.22);
    font-size: 20px;
    padding: 0;
}
QPushButton#sidebar_btn:hover {
    background: rgba(124,111,255,0.14);
    color: rgba(255,255,255,0.65);
}
QPushButton#sidebar_btn:checked {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(124,111,255,0.32),
        stop:1 rgba(124,111,255,0.18)
    );
    color: #a78bfa;
    border: 1px solid rgba(124,111,255,0.30);
}
QToolTip {
    background: #12101f;
    color: #d4d4f0;
    border: 1px solid rgba(124,111,255,0.35);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 12px;
    font-weight: 500;
}


/* ══════════════════════════════════════════════════════════════════════
   TOP BAR & STRUCTURAL FRAMES
   ══════════════════════════════════════════════════════════════════════ */
QWidget#top_bar { background: #07070d; border: none; }
QFrame#top_separator {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 transparent, stop:0.3 rgba(124,111,255,0.15),
        stop:0.7 rgba(124,111,255,0.15), stop:1 transparent);
    border: none;
    max-height: 1px;
}
QWidget#content_wrapper, QWidget#right_panel { background: transparent; }

QFrame#status_bar {
    background: #090717;
    border-top: 1px solid rgba(255,255,255,0.04);
}
QLabel#status_label {
    color: #30303e;
    font-size: 11px;
    background: transparent;
}


/* ══════════════════════════════════════════════════════════════════════
   GLASS CARDS
   ══════════════════════════════════════════════════════════════════════ */
QFrame#card {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
}
QFrame#stat_card {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(255,255,255,0.045),
        stop:1 rgba(255,255,255,0.025)
    );
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
}
QFrame#stat_card:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(124,111,255,0.10),
        stop:1 rgba(124,111,255,0.04)
    );
    border-color: rgba(124,111,255,0.30);
}


/* ══════════════════════════════════════════════════════════════════════
   TYPOGRAPHY
   ══════════════════════════════════════════════════════════════════════ */
QLabel#h1 {
    font-size: 22px;
    font-weight: 700;
    color: #f4f4ff;
    letter-spacing: -0.5px;
    background: transparent;
}
QLabel#h2 {
    font-size: 14px;
    font-weight: 600;
    color: #d0d0f0;
    background: transparent;
}
QLabel#muted {
    color: #48486a;
    font-size: 11px;
    background: transparent;
}
QLabel#alert_banner {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(220,38,38,0.18), stop:1 rgba(220,38,38,0.10));
    color: #fca5a5;
    border: 1px solid rgba(220,38,38,0.28);
    border-left: 3px solid #dc2626;
    border-radius: 0;
    padding: 6px 16px;
    font-weight: 600;
    font-size: 12px;
}


/* ══════════════════════════════════════════════════════════════════════
   BUTTONS
   ══════════════════════════════════════════════════════════════════════ */
QPushButton {
    background: rgba(255,255,255,0.055);
    color: #c0c0d8;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 9px;
    padding: 6px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover {
    background: rgba(255,255,255,0.10);
    border-color: rgba(255,255,255,0.16);
    color: #f4f4ff;
}
QPushButton:pressed {
    background: rgba(124,111,255,0.18);
    border-color: rgba(124,111,255,0.40);
    color: #f4f4ff;
}
QPushButton:disabled {
    background: rgba(255,255,255,0.02);
    color: #28283a;
    border-color: rgba(255,255,255,0.04);
}
QPushButton:checked {
    background: rgba(124,111,255,0.20);
    border-color: rgba(124,111,255,0.42);
    color: #a78bfa;
}

QPushButton#primary {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c6fff, stop:1 #5a50e0
    );
    color: #ffffff;
    border: 1px solid rgba(124,111,255,0.50);
    font-weight: 700;
    letter-spacing: 0.2px;
}
QPushButton#primary:hover {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #9a88ff, stop:1 #7060f0
    );
    border-color: rgba(154,136,255,0.70);
}
QPushButton#primary:pressed {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #5040c8, stop:1 #4030b0
    );
}

/* Danger variant for destructive actions */
QPushButton#danger {
    background: rgba(220,38,38,0.12);
    color: #fca5a5;
    border: 1px solid rgba(220,38,38,0.28);
    font-weight: 600;
}
QPushButton#danger:hover {
    background: rgba(220,38,38,0.22);
    border-color: rgba(220,38,38,0.50);
    color: #fee2e2;
}

/* Success / confirm variant */
QPushButton#success {
    background: rgba(52,211,153,0.12);
    color: #6ee7b7;
    border: 1px solid rgba(52,211,153,0.28);
    font-weight: 600;
}
QPushButton#success:hover {
    background: rgba(52,211,153,0.22);
    border-color: rgba(52,211,153,0.50);
    color: #a7f3d0;
}


/* ══════════════════════════════════════════════════════════════════════
   INPUTS
   ══════════════════════════════════════════════════════════════════════ */
QLineEdit, QComboBox {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 9px;
    padding: 7px 12px;
    color: #e4e4f8;
    selection-background-color: rgba(124,111,255,0.55);
    selection-color: #ffffff;
}
QLineEdit:hover, QComboBox:hover {
    border-color: rgba(255,255,255,0.14);
    background: rgba(255,255,255,0.065);
}
QLineEdit:focus, QComboBox:focus {
    border-color: #7c6fff;
    background: rgba(124,111,255,0.08);
    color: #f4f4ff;
}
QLineEdit:disabled, QComboBox:disabled {
    background: rgba(255,255,255,0.02);
    color: #30303e;
    border-color: rgba(255,255,255,0.04);
}
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid rgba(124,111,255,0.80);
    width: 0; height: 0;
}
QComboBox QAbstractItemView {
    background: #11101f;
    border: 1px solid rgba(124,111,255,0.18);
    border-radius: 10px;
    selection-background-color: rgba(124,111,255,0.22);
    selection-color: #f4f4ff;
    color: #c0c0d8;
    outline: none;
    padding: 4px;
}
QComboBox QAbstractItemView::item { padding: 7px 14px; border-radius: 6px; }
QPlainTextEdit, QTextEdit {
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 11px;
    padding: 10px;
    color: #e4e4f8;
    selection-background-color: rgba(124,111,255,0.50);
    line-height: 1.5;
}
QPlainTextEdit:focus, QTextEdit:focus {
    border-color: rgba(124,111,255,0.60);
    background: rgba(124,111,255,0.055);
}
QSpinBox, QDoubleSpinBox {
    background: rgba(255,255,255,0.045);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 9px;
    padding: 6px 10px;
    color: #e4e4f8;
}
QSpinBox:focus, QDoubleSpinBox:focus { border-color: #7c6fff; }
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: rgba(255,255,255,0.05);
    border: none;
    width: 18px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {
    background: rgba(124,111,255,0.18);
}


/* ══════════════════════════════════════════════════════════════════════
   TABLES
   ══════════════════════════════════════════════════════════════════════ */
QTableView, QTableWidget {
    background: transparent;
    border: none;
    gridline-color: rgba(255,255,255,0.028);
    alternate-background-color: rgba(255,255,255,0.012);
    selection-background-color: rgba(124,111,255,0.20);
    selection-color: #f4f4ff;
    outline: none;
}
QTableView::item {
    padding: 5px 10px;
    border: none;
    color: #b0b0cc;
    border-bottom: 1px solid rgba(255,255,255,0.022);
}
QTableView::item:selected {
    background: rgba(124,111,255,0.20);
    color: #f4f4ff;
    border-bottom-color: rgba(124,111,255,0.30);
}
QTableView::item:hover:!selected {
    background: rgba(255,255,255,0.032);
    color: #d0d0e8;
}

QHeaderView { background: transparent; border: none; }
QHeaderView::section {
    background: rgba(255,255,255,0.030);
    color: #484870;
    border: none;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    border-right: 1px solid rgba(255,255,255,0.028);
    padding: 9px 10px;
    font-weight: 700;
    font-size: 10px;
    letter-spacing: 1.0px;
    text-transform: uppercase;
}
QHeaderView::section:hover {
    background: rgba(124,111,255,0.09);
    color: #9090c0;
}
QHeaderView::section:checked { color: #7c6fff; }
QHeaderView::section:last { border-right: none; }


/* ══════════════════════════════════════════════════════════════════════
   LIST WIDGET
   ══════════════════════════════════════════════════════════════════════ */
QListWidget {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    outline: none;
}
QListWidget::item {
    padding: 7px 14px;
    border-radius: 8px;
    color: #b0b0cc;
}
QListWidget::item:hover  { background: rgba(255,255,255,0.04); color: #d0d0e8; }
QListWidget::item:selected {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(124,111,255,0.24), stop:1 rgba(124,111,255,0.14));
    color: #f4f4ff;
    border-left: 2px solid #7c6fff;
    padding-left: 12px;
}


/* ══════════════════════════════════════════════════════════════════════
   PROGRESS BAR
   ══════════════════════════════════════════════════════════════════════ */
QProgressBar {
    background: rgba(255,255,255,0.05);
    border: none;
    border-radius: 5px;
    text-align: center;
    color: transparent;
    height: 6px;
}
QProgressBar::chunk {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 #7c6fff, stop:0.5 #a78bfa, stop:1 #38bdf8
    );
    border-radius: 5px;
}


/* ══════════════════════════════════════════════════════════════════════
   GROUP BOXES
   ══════════════════════════════════════════════════════════════════════ */
QGroupBox {
    background: rgba(255,255,255,0.022);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px;
    margin-top: 18px;
    padding-top: 12px;
    font-weight: 600;
    color: #a0a0c0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    padding: 0 8px;
    color: rgba(124,111,255,0.80);
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    text-transform: uppercase;
    background: #07070d;
    border-radius: 4px;
}


/* ══════════════════════════════════════════════════════════════════════
   CHECKBOX & RADIO
   ══════════════════════════════════════════════════════════════════════ */
QCheckBox, QRadioButton {
    color: #b0b0cc;
    spacing: 9px;
    font-size: 13px;
}
QCheckBox:hover, QRadioButton:hover { color: #f4f4ff; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1.5px solid rgba(255,255,255,0.16);
    border-radius: 5px;
    background: rgba(255,255,255,0.04);
}
QCheckBox::indicator:hover { border-color: rgba(124,111,255,0.70); }
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6fff,stop:1 #5a50e0);
    border-color: rgba(124,111,255,0.70);
    image: none;
}
QRadioButton::indicator {
    width: 16px; height: 16px;
    border: 1.5px solid rgba(255,255,255,0.16);
    border-radius: 9px;
    background: rgba(255,255,255,0.04);
}
QRadioButton::indicator:hover { border-color: rgba(124,111,255,0.70); }
QRadioButton::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6fff,stop:1 #5a50e0);
    border-color: rgba(124,111,255,0.70);
}


/* ══════════════════════════════════════════════════════════════════════
   SCROLLBARS
   ══════════════════════════════════════════════════════════════════════ */
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: rgba(124,111,255,0.50); }
QScrollBar::handle:vertical:pressed { background: rgba(124,111,255,0.80); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background: transparent;
    height: 6px;
    margin: 0 2px;
}
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.08);
    border-radius: 3px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: rgba(124,111,255,0.50); }
QScrollBar::handle:horizontal:pressed { background: rgba(124,111,255,0.80); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }


/* ══════════════════════════════════════════════════════════════════════
   POSTER CARD
   ══════════════════════════════════════════════════════════════════════ */
QFrame#poster_card { background: transparent; border: none; }


/* ══════════════════════════════════════════════════════════════════════
   DIALOGS & MESSAGE BOXES
   ══════════════════════════════════════════════════════════════════════ */
QMessageBox {
    background: #0e0c1c;
    border: 1px solid rgba(124,111,255,0.18);
    border-radius: 14px;
}
QMessageBox QLabel { color: #c0c0d8; font-size: 13px; }
QMessageBox QPushButton { min-width: 90px; padding: 7px 22px; }


/* ══════════════════════════════════════════════════════════════════════
   TAB WIDGET
   ══════════════════════════════════════════════════════════════════════ */
QTabWidget::pane {
    background: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    top: -1px;
}
QTabBar::tab {
    background: rgba(255,255,255,0.025);
    color: #48486a;
    border: 1px solid rgba(255,255,255,0.06);
    border-bottom: none;
    border-radius: 9px 9px 0 0;
    padding: 7px 20px;
    margin-right: 2px;
    font-weight: 500;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 rgba(124,111,255,0.20), stop:1 rgba(124,111,255,0.10));
    color: #d0c8ff;
    border-color: rgba(124,111,255,0.30);
    border-bottom-color: rgba(124,111,255,0.10);
    font-weight: 700;
}
QTabBar::tab:hover:!selected {
    background: rgba(255,255,255,0.05);
    color: #8888b0;
}


/* ══════════════════════════════════════════════════════════════════════
   SPLITTER
   ══════════════════════════════════════════════════════════════════════ */
QSplitter::handle {
    background: rgba(255,255,255,0.05);
    width: 1px;
}
QSplitter::handle:hover { background: rgba(124,111,255,0.55); }
QSplitter::handle:pressed { background: #7c6fff; }


/* ══════════════════════════════════════════════════════════════════════
   SEPARATOR LINES
   ══════════════════════════════════════════════════════════════════════ */
QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.06);
    border: none;
    max-height: 1px;
}


/* ══════════════════════════════════════════════════════════════════════
   CONTEXT / POPUP MENUS
   ══════════════════════════════════════════════════════════════════════ */
QMenu {
    background: #0f0e1e;
    border: 1px solid rgba(124,111,255,0.20);
    border-radius: 13px;
    padding: 6px;
    color: #c0c0d8;
}
QMenu::item {
    padding: 8px 32px 8px 16px;
    border-radius: 8px;
    font-size: 13px;
}
QMenu::item:selected {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(124,111,255,0.22), stop:1 rgba(124,111,255,0.12));
    color: #f4f4ff;
}
QMenu::separator {
    height: 1px;
    background: rgba(255,255,255,0.06);
    margin: 5px 12px;
}
QMenu::icon { padding-left: 6px; }


/* ══════════════════════════════════════════════════════════════════════
   FORM LAYOUT LABELS
   ══════════════════════════════════════════════════════════════════════ */
QFormLayout QLabel {
    color: #606088;
    font-size: 12px;
    font-weight: 500;
    min-width: 120px;
}


/* ══════════════════════════════════════════════════════════════════════
   SLIDER
   ══════════════════════════════════════════════════════════════════════ */
QSlider::groove:horizontal {
    background: rgba(255,255,255,0.08);
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #7c6fff;
    border: 2px solid rgba(124,111,255,0.50);
    width: 14px; height: 14px;
    border-radius: 8px;
    margin: -5px 0;
}
QSlider::handle:horizontal:hover {
    background: #9a88ff;
    border-color: rgba(154,136,255,0.70);
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #7c6fff, stop:1 #a78bfa);
    border-radius: 2px;
}


/* ══════════════════════════════════════════════════════════════════════
   BADGE / NOTIFICATION LABELS  (objectName="badge")
   ══════════════════════════════════════════════════════════════════════ */
QLabel#badge {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6fff,stop:1 #5a50e0);
    color: #ffffff;
    border-radius: 9px;
    font-size: 9px;
    font-weight: 800;
    padding: 1px 5px;
    min-width: 16px;
}
QLabel#badge_red {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef4444,stop:1 #dc2626);
    color: #ffffff;
    border-radius: 9px;
    font-size: 9px;
    font-weight: 800;
    padding: 1px 5px;
    min-width: 16px;
}
QLabel#badge_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #34d399,stop:1 #10b981);
    color: #ffffff;
    border-radius: 9px;
    font-size: 9px;
    font-weight: 800;
    padding: 1px 5px;
    min-width: 16px;
}


/* ══════════════════════════════════════════════════════════════════════
   GLOBAL SEARCH BAR  (objectName="search_bar")
   ══════════════════════════════════════════════════════════════════════ */
QLineEdit#search_bar {
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 20px;
    padding: 8px 18px;
    font-size: 13px;
    color: #e4e4f8;
}
QLineEdit#search_bar:focus {
    background: rgba(124,111,255,0.09);
    border-color: rgba(124,111,255,0.65);
}


/* ══════════════════════════════════════════════════════════════════════
   LOADING / PLACEHOLDER STATES
   ══════════════════════════════════════════════════════════════════════ */
QLabel#placeholder {
    color: #28283a;
    font-size: 28px;
    background: transparent;
}
QLabel#placeholder_sub {
    color: #303048;
    font-size: 13px;
    background: transparent;
}

"""


# ══════════════════════════════════════════════════════════════════════
# LIGHT THEME
# ══════════════════════════════════════════════════════════════════════
LIGHT_STYLESHEET = """

QMainWindow, QDialog { background: #f0f0f8; color: #14142a; }
QWidget {
    background: #f0f0f8;
    color: #14142a;
    font-family: 'Segoe UI', 'Inter', 'SF Pro Display', system-ui, sans-serif;
    font-size: 13px;
}
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }

QWidget#title_bar {
    background: rgba(255,255,255,0.92);
    border-bottom: 1px solid rgba(0,0,0,0.07);
}
QLabel#title_bar_label {
    color: rgba(0,0,0,0.32); font-size: 11px;
    font-weight: 600; letter-spacing: 1.2px; background: transparent;
}
QPushButton#wc_min, QPushButton#wc_max {
    background: rgba(0,0,0,0.04); border: 1px solid rgba(0,0,0,0.06);
    border-radius: 6px; color: rgba(0,0,0,0.30); font-size: 12px;
}
QPushButton#wc_min:hover, QPushButton#wc_max:hover {
    background: rgba(0,0,0,0.08); color: #14142a;
}
QPushButton#wc_close {
    background: rgba(0,0,0,0.04); border: 1px solid rgba(0,0,0,0.06);
    border-radius: 6px; color: rgba(0,0,0,0.30); font-size: 12px;
}
QPushButton#wc_close:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef4444,stop:1 #dc2626);
    border-color: rgba(220,38,38,0.50); color: #fff;
}

QFrame#sidebar {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #eceaf6, stop:0.5 #eae8f4, stop:1 #eceaf6);
    border-right: 1px solid rgba(0,0,0,0.06);
}
QLabel#sidebar_logo { color: #6c5fff; font-size: 24px; background: transparent; }
QFrame#sidebar_divider { background: rgba(0,0,0,0.07); border: none; max-height: 1px; }
QPushButton#sidebar_btn {
    background: transparent; border: none; border-radius: 14px;
    color: rgba(0,0,0,0.25); font-size: 20px; padding: 0;
}
QPushButton#sidebar_btn:hover { background: rgba(108,95,255,0.10); color: rgba(0,0,0,0.60); }
QPushButton#sidebar_btn:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 rgba(108,95,255,0.22), stop:1 rgba(108,95,255,0.12));
    color: #6c5fff;
    border: 1px solid rgba(108,95,255,0.28);
}
QToolTip {
    background: #ffffff; color: #14142a;
    border: 1px solid rgba(108,95,255,0.28);
    border-radius: 8px; padding: 6px 14px; font-size: 12px;
}

QWidget#top_bar { background: #f0f0f8; border: none; }
QFrame#top_separator {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 transparent, stop:0.3 rgba(108,95,255,0.18),
        stop:0.7 rgba(108,95,255,0.18), stop:1 transparent);
    border: none; max-height: 1px;
}
QWidget#content_wrapper, QWidget#right_panel { background: transparent; }
QFrame#status_bar { background: #eceaf6; border-top: 1px solid rgba(0,0,0,0.06); }
QLabel#status_label { color: #9898b8; font-size: 11px; background: transparent; }

QFrame#card {
    background: rgba(255,255,255,0.82);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 18px;
}
QFrame#stat_card {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 rgba(255,255,255,0.95), stop:1 rgba(255,255,255,0.80));
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 18px;
}
QFrame#stat_card:hover {
    border-color: rgba(108,95,255,0.35);
    background: rgba(108,95,255,0.04);
}

QLabel#h1 { font-size: 22px; font-weight: 700; color: #0c0c22; letter-spacing: -0.5px; background: transparent; }
QLabel#h2 { font-size: 14px; font-weight: 600; color: #26263e; background: transparent; }
QLabel#muted { color: #8888a8; font-size: 11px; background: transparent; }
QLabel#alert_banner {
    background: rgba(220,38,38,0.08); color: #b91c1c;
    border: 1px solid rgba(220,38,38,0.20); border-left: 3px solid #dc2626;
    border-radius: 0; padding: 6px 16px; font-weight: 600; font-size: 12px;
}

QPushButton {
    background: rgba(255,255,255,0.90); color: #26263e;
    border: 1px solid rgba(0,0,0,0.11); border-radius: 9px;
    padding: 6px 16px; font-size: 13px; font-weight: 500;
}
QPushButton:hover { background: #ffffff; border-color: rgba(108,95,255,0.40); color: #0c0c22; }
QPushButton:pressed { background: rgba(108,95,255,0.09); border-color: rgba(108,95,255,0.35); }
QPushButton:disabled { background: #efefef; color: #b0b0c8; border-color: rgba(0,0,0,0.06); }
QPushButton:checked { background: rgba(108,95,255,0.12); border-color: rgba(108,95,255,0.35); color: #5040c8; }
QPushButton#primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c6fff,stop:1 #5a50e0);
    color: #fff; border: none; font-weight: 700;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #9a88ff,stop:1 #7060f0);
}
QPushButton#danger {
    background: rgba(220,38,38,0.08); color: #b91c1c;
    border: 1px solid rgba(220,38,38,0.22); font-weight: 600;
}
QPushButton#danger:hover { background: rgba(220,38,38,0.16); border-color: rgba(220,38,38,0.40); }
QPushButton#success {
    background: rgba(16,185,129,0.08); color: #065f46;
    border: 1px solid rgba(16,185,129,0.25); font-weight: 600;
}
QPushButton#success:hover { background: rgba(16,185,129,0.16); border-color: rgba(16,185,129,0.40); }

QLineEdit, QComboBox {
    background: rgba(255,255,255,0.95); border: 1px solid rgba(0,0,0,0.12);
    border-radius: 9px; padding: 7px 12px; color: #14142a;
    selection-background-color: rgba(124,111,255,0.35);
}
QLineEdit:hover, QComboBox:hover { border-color: rgba(108,95,255,0.35); }
QLineEdit:focus, QComboBox:focus { border-color: #7c6fff; background: rgba(108,95,255,0.04); }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 5px solid #7c6fff; width: 0; height: 0; }
QComboBox QAbstractItemView {
    background: #ffffff; border: 1px solid rgba(108,95,255,0.18);
    border-radius: 10px; selection-background-color: rgba(108,95,255,0.12);
    color: #14142a; outline: none; padding: 4px;
}
QPlainTextEdit, QTextEdit {
    background: #ffffff; border: 1px solid rgba(0,0,0,0.10);
    border-radius: 11px; padding: 10px; color: #14142a;
}
QPlainTextEdit:focus, QTextEdit:focus { border-color: #7c6fff; }

QTableView, QTableWidget {
    background: transparent; border: none;
    gridline-color: rgba(0,0,0,0.04);
    alternate-background-color: rgba(0,0,0,0.012);
    selection-background-color: rgba(108,95,255,0.12);
    selection-color: #0c0c22; outline: none;
}
QTableView::item { padding: 5px 10px; border: none; color: #36364e; border-bottom: 1px solid rgba(0,0,0,0.04); }
QTableView::item:selected { background: rgba(108,95,255,0.12); color: #0c0c22; }
QTableView::item:hover:!selected { background: rgba(0,0,0,0.020); }
QHeaderView::section {
    background: rgba(0,0,0,0.025); color: #7878a0; border: none;
    border-bottom: 1px solid rgba(0,0,0,0.07);
    padding: 9px 10px; font-weight: 700; font-size: 10px; letter-spacing: 1.0px;
}
QHeaderView::section:hover { background: rgba(108,95,255,0.06); color: #5050a0; }

QListWidget {
    background: rgba(255,255,255,0.80); border: 1px solid rgba(0,0,0,0.07);
    border-radius: 12px; outline: none;
}
QListWidget::item { padding: 7px 14px; border-radius: 8px; color: #36364e; }
QListWidget::item:hover { background: rgba(0,0,0,0.03); }
QListWidget::item:selected {
    background: rgba(108,95,255,0.12); color: #0c0c22;
    border-left: 2px solid #7c6fff; padding-left: 12px;
}

QProgressBar { background: rgba(0,0,0,0.07); border: none; border-radius: 5px; height: 6px; }
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c6fff,stop:0.5 #a78bfa,stop:1 #38bdf8);
    border-radius: 5px;
}

QGroupBox {
    background: rgba(255,255,255,0.70); border: 1px solid rgba(0,0,0,0.07);
    border-radius: 14px; margin-top: 18px; padding-top: 12px;
    font-weight: 600; color: #36364e;
}
QGroupBox::title {
    subcontrol-origin: margin; left: 16px; padding: 0 8px;
    color: #7c6fff; font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
    background: #f0f0f8; border-radius: 4px;
}

QCheckBox, QRadioButton { color: #36364e; spacing: 9px; }
QCheckBox:hover, QRadioButton:hover { color: #0c0c22; }
QCheckBox::indicator {
    width: 16px; height: 16px; border: 1.5px solid rgba(0,0,0,0.18);
    border-radius: 5px; background: rgba(255,255,255,0.95);
}
QCheckBox::indicator:hover { border-color: rgba(108,95,255,0.60); }
QCheckBox::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6fff,stop:1 #5a50e0);
    border-color: rgba(124,111,255,0.60);
}
QRadioButton::indicator {
    width: 16px; height: 16px; border: 1.5px solid rgba(0,0,0,0.18);
    border-radius: 9px; background: rgba(255,255,255,0.95);
}
QRadioButton::indicator:checked {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6fff,stop:1 #5a50e0);
    border-color: rgba(124,111,255,0.60);
}

QScrollBar:vertical { background: transparent; width: 6px; }
QScrollBar::handle:vertical { background: rgba(0,0,0,0.12); border-radius: 3px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: rgba(108,95,255,0.50); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 6px; }
QScrollBar::handle:horizontal { background: rgba(0,0,0,0.12); border-radius: 3px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: rgba(108,95,255,0.50); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QFrame#poster_card { background: transparent; border: none; }

QMessageBox {
    background: #f8f8fc;
    border: 1px solid rgba(108,95,255,0.15);
    border-radius: 14px;
}
QMessageBox QLabel { color: #14142a; }
QMessageBox QPushButton { min-width: 90px; padding: 7px 22px; }

QTabWidget::pane {
    background: rgba(255,255,255,0.70); border: 1px solid rgba(0,0,0,0.07);
    border-radius: 12px; top: -1px;
}
QTabBar::tab {
    background: rgba(255,255,255,0.50); color: #6868a0;
    border: 1px solid rgba(0,0,0,0.07); border-bottom: none;
    border-radius: 9px 9px 0 0; padding: 7px 20px; margin-right: 2px;
    font-weight: 500; font-size: 12px;
}
QTabBar::tab:selected {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 rgba(108,95,255,0.14), stop:1 rgba(108,95,255,0.06));
    color: #5040c8; border-color: rgba(108,95,255,0.25); font-weight: 700;
}
QTabBar::tab:hover:!selected { background: rgba(255,255,255,0.80); color: #4848a0; }

QSplitter::handle { background: rgba(0,0,0,0.05); width: 1px; }
QSplitter::handle:hover { background: rgba(108,95,255,0.55); }

QFrame[frameShape="4"], QFrame[frameShape="5"] {
    color: rgba(0,0,0,0.07); background: rgba(0,0,0,0.07);
    border: none; max-height: 1px;
}

QMenu {
    background: #ffffff; border: 1px solid rgba(108,95,255,0.18);
    border-radius: 13px; padding: 6px; color: #14142a;
}
QMenu::item { padding: 8px 32px 8px 16px; border-radius: 8px; font-size: 13px; }
QMenu::item:selected {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 rgba(108,95,255,0.14), stop:1 rgba(108,95,255,0.07));
    color: #0c0c22;
}
QMenu::separator { height: 1px; background: rgba(0,0,0,0.07); margin: 5px 12px; }

QFormLayout QLabel { color: #7878a0; font-size: 12px; font-weight: 500; min-width: 120px; }

QSlider::groove:horizontal { background: rgba(0,0,0,0.10); height: 4px; border-radius: 2px; }
QSlider::handle:horizontal {
    background: #7c6fff; border: 2px solid rgba(124,111,255,0.50);
    width: 14px; height: 14px; border-radius: 8px; margin: -5px 0;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #7c6fff,stop:1 #a78bfa);
    border-radius: 2px;
}

QLabel#badge {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #7c6fff,stop:1 #5a50e0);
    color: #fff; border-radius: 9px; font-size: 9px; font-weight: 800; padding: 1px 5px;
}
QLabel#badge_red {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #ef4444,stop:1 #dc2626);
    color: #fff; border-radius: 9px; font-size: 9px; font-weight: 800; padding: 1px 5px;
}
QLabel#badge_green {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #34d399,stop:1 #10b981);
    color: #fff; border-radius: 9px; font-size: 9px; font-weight: 800; padding: 1px 5px;
}

QLineEdit#search_bar {
    background: rgba(255,255,255,0.90); border: 1px solid rgba(0,0,0,0.12);
    border-radius: 20px; padding: 8px 18px; font-size: 13px; color: #14142a;
}
QLineEdit#search_bar:focus { border-color: #7c6fff; background: rgba(108,95,255,0.05); }

QLabel#placeholder { color: #b8b8d0; font-size: 28px; background: transparent; }
QLabel#placeholder_sub { color: #c8c8e0; font-size: 13px; background: transparent; }

"""


def get_stylesheet(theme: str = "dark") -> str:
    return DARK_STYLESHEET if theme.lower() == "dark" else LIGHT_STYLESHEET


# Backwards-compatibility alias — bootstrap.py imports APP_STYLESHEET directly
APP_STYLESHEET = DARK_STYLESHEET
