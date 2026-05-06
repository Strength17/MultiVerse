# ui/history_panel.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from ui.styles import COLORS

class HistoryPanel(QWidget):
    """Scrollable history of sent verses."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("historyPanel")
        
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("SESSION HISTORY"))
        
        self.history_display = QTextEdit()
        self.history_display.setReadOnly(True)
        self.history_display.setStyleSheet(f"background-color: {COLORS['bg_panel']}; color: {COLORS['text_primary']}; border: none;")
        layout.addWidget(self.history_display)
        
    def add_history_entry(self, ref: str):
        self.history_display.append(ref)
