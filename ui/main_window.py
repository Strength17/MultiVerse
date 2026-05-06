# ui/main_window.py

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QComboBox, QPushButton
from PyQt6.QtCore import Qt, QSize
from ui.styles import COLORS, FONTS
from ui.audio_meter import AudioMeterWidget
from ui.transcript_panel import TranscriptPanel
from ui.approval_panel import ApprovalPanel
from ui.manual_lookup import ManualLookup
from core.audio_capture import AudioCapture

class MainWindow(QMainWindow):
    def __init__(self, config, db):
        super().__init__()
        self._config = config
        self._db = db
        self.setWindowTitle("MultiVerse v1.0.0")
        self.setMinimumSize(1200, 700)
        
        # Central widget and layout
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("● MultiVerse"))
        self._device_combo = QComboBox()
        # Populate devices here...
        header.addWidget(self._device_combo)
        self._start_btn = QPushButton("▶ START")
        self._start_btn.setObjectName("btn_primary")
        header.addWidget(self._start_btn)
        main_layout.addLayout(header)
        
        # Splitter Layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.left_panel = QWidget()
        self.left_panel.setObjectName("panel_left")
        left_layout = QVBoxLayout(self.left_panel)
        self.audio_meter = AudioMeterWidget()
        left_layout.addWidget(QLabel("AUDIO METER"))
        left_layout.addWidget(self.audio_meter)
        self.transcript_panel = TranscriptPanel()
        left_layout.addWidget(QLabel("LIVE TRANSCRIPT"))
        left_layout.addWidget(self.transcript_panel)
        
        self.center_panel = QWidget()
        self.center_panel.setObjectName("panel_center")
        center_layout = QVBoxLayout(self.center_panel)
        self.approval_panel = ApprovalPanel()
        center_layout.addWidget(self.approval_panel)
        
        self.right_panel = QWidget()
        self.right_panel.setObjectName("panel_right")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.addWidget(QLabel("VERSE HISTORY"))
        
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.center_panel)
        splitter.addWidget(self.right_panel)
        
        main_layout.addWidget(splitter)
        
        # Bottom Manual Search
        self.manual_lookup = ManualLookup(self._db)
        main_layout.addWidget(self.manual_lookup)
        
        # Set splitter sizes from config
        sizes = [int(s) for s in self._config["ui"]["splitter_sizes"].split(",")]
        splitter.setSizes(sizes)
