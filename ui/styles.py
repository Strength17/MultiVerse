# ui/styles.py

"""
Defines the dark theme stylesheet for the MultiVerse PyQt6 application.
This stylesheet provides a consistent dark aesthetic suitable for low-light AV control environments.
"""

DARK_THEME_STYLESHEET = """
/* General application style */
QWidget {
    background-color: #2b2b2b; /* Dark Gray */
    color: #f0f0f0;            /* Light Gray for text */
    selection-background-color: #0078d7; /* Standard blue for selection */
    selection-color: #ffffff;
}

/* Main window and container widgets */
QMainWindow, QFrame, QGroupBox, QTabWidget::pane {
    background-color: #202020; /* Even darker for primary backgrounds */
    border: 1px solid #3a3a3a;
}

/* Labels */
QLabel {
    color: #f0f0f0;
}

/* Push Buttons */
QPushButton {
    background-color: #3a3a3a;
    color: #f0f0f0;
    border: 1px solid #5a5a5a;
    padding: 5px 10px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #4a4a4a;
    border: 1px solid #6a6a6a;
}
QPushButton:pressed {
    background-color: #0078d7;
    border: 1px solid #005bb7;
}
QPushButton:disabled {
    background-color: #2b2b2b;
    color: #707070;
    border: 1px solid #4a4a4a;
}

/* Line Edits (text input) */
QLineEdit, QTextEdit {
    background-color: #3a3a3a;
    color: #f0f0f0;
    border: 1px solid #5a5a5a;
    padding: 3px;
    border-radius: 3px;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #0078d7;
}

/* Combo Box */
QComboBox {
    background-color: #3a3a3a;
    color: #f0f0f0;
    border: 1px solid #5a5a5a;
    padding: 3px;
    border-radius: 3px;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 20px;
    border-left-width: 1px;
    border-left-color: #5a5a5a;
    border-left-style: solid;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
}
/* QComboBox::down-arrow {
    image: url(resources/down_arrow_dark.png);
} */
QComboBox QAbstractItemView {
    background-color: #3a3a3a;
    selection-background-color: #0078d7;
    color: #f0f0f0;
}

/* Scroll Bars */
QScrollBar:vertical {
    border: 1px solid #3a3a3a;
    background: #2b2b2b;
    width: 10px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #5a5a5a;
    min-height: 20px;
    border-radius: 2px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: none;
}
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

/* Sliders */
QSlider::groove:horizontal {
    border: 1px solid #4a4a4a;
    height: 8px;
    background: #3a3a3a;
    margin: 2px 0;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #0078d7;
    border: 1px solid #005bb7;
    width: 18px;
    margin: -5px 0;
    border-radius: 9px;
}
QSlider::groove:vertical {
    border: 1px solid #4a4a4a;
    width: 8px;
    background: #3a3a3a;
    margin: 0 2px;
    border-radius: 4px;
}
QSlider::handle:vertical {
    background: #0078d7;
    border: 1px solid #005bb7;
    height: 18px;
    margin: 0 -5px;
    border-radius: 9px;
}

/* Checkboxes */
QCheckBox::indicator {
    width: 13px;
    height: 13px;
    border: 1px solid #5a5a5a;
    border-radius: 3px;
    background-color: #3a3a3a;
}
QCheckBox::indicator:checked {
    background-color: #0078d7;
    /* image: url(resources/checked_dark.png); */
}
QCheckBox::indicator:disabled {
    background-color: #2b2b2b;
    border: 1px solid #4a4a4a;
}
"""
