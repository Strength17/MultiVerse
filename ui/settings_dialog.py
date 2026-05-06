# ui/settings_dialog.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QLabel, QLineEdit, QCheckBox, QPushButton
from ui.styles import COLORS

class SettingsDialog(QDialog):
    """Application settings dialog with 4 tabs."""
    
    def __init__(self, config_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # Tabs
        self.tabs.addTab(QWidget(), "Audio")
        self.tabs.addTab(QWidget(), "Detection")
        self.tabs.addTab(QWidget(), "Display")
        self.tabs.addTab(QWidget(), "Session")
        
        layout.addWidget(self.tabs)
        
        btn = QPushButton("Save & Close")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)
