# ui/main_window.py

import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QSplitter, QLabel, QComboBox, QPushButton, QStatusBar)
from PyQt6.QtCore import Qt, QSize, pyqtSlot, QThread
from ui.styles import COLORS, FONTS
from ui.audio_meter import AudioMeterWidget
from ui.transcript_panel import TranscriptPanel
from ui.approval_panel import ApprovalPanel
from ui.manual_lookup import ManualLookup
from ui.history_panel import HistoryPanel
from core.transcription_worker import TranscriptionWorker
from core.audio_capture import AudioCapture

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, config, db):
        super().__init__()
        self._config = config
        self._db = db
        self.setWindowTitle("MultiVerse v1.0.0")
        self.setMinimumSize(1200, 700)
        
        # Core components for wiring
        self.worker = None
        self.worker_thread = None
        
        # Central widget and layout
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        
        # Header
        header = QHBoxLayout()
        header.addWidget(QLabel("● MultiVerse"))
        
        self._device_combo = QComboBox()
        self._populate_devices()
        header.addWidget(self._device_combo)
        
        self._start_btn = QPushButton("▶ START")
        self._start_btn.setObjectName("btn_primary")
        self._start_btn.clicked.connect(self.toggle_transcription)
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
        self.history_panel = HistoryPanel()
        right_layout.addWidget(self.history_panel)
        
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.center_panel)
        splitter.addWidget(self.right_panel)
        
        main_layout.addWidget(splitter)
        
        # Bottom Manual Search
        self.manual_lookup = ManualLookup(self._db)
        main_layout.addWidget(self.manual_lookup)
        
        # Set splitter sizes from config
        try:
            sizes = [int(s) for s in self._config["ui"]["splitter_sizes"].split(",")]
            splitter.setSizes(sizes)
        except (KeyError, ValueError):
            splitter.setSizes([300, 600, 300])

        # Startup Status Bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Waking up AI engine...")
        self._status_bar.setStyleSheet(f"QStatusBar {{ font-size: 10px; color: {COLORS['text_muted']}; border-top: 1px solid {COLORS['border']}; }}")

    def _populate_devices(self):
        """Fills the device combo box with available audio inputs."""
        try:
            devices = AudioCapture.get_devices()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    self._device_combo.addItem(f"{i}: {dev['name']}", i)
            
            # Select default from config
            default_idx = self._config.getint('audio', 'input_device_index', fallback=0)
            target_idx = self._device_combo.findData(default_idx)
            if target_idx != -1:
                self._device_combo.setCurrentIndex(target_idx)
        except Exception as e:
            logger.error(f"Failed to populate audio devices: {e}")

    @pyqtSlot()
    def toggle_transcription(self):
        """Starts or stops the transcription worker."""
        if self.worker and self.worker.is_running:
            self.stop_worker()
        else:
            self.start_worker()

    def start_worker(self):
        """Initializes and starts the background transcription thread."""
        # Update config with selected device
        selected_device = self._device_combo.currentData()
        self._config.set('audio', 'input_device_index', str(selected_device))
        
        self.worker_thread = QThread()
        self.worker = TranscriptionWorker(self._config, self._db)
        
        # Enable AI detection if models are already loaded
        if hasattr(self, '_ai_model'):
            self.worker.enable_detection(self._ai_model, self._ai_matrix, self._ai_refs)
            
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker_thread.started.connect(self.worker.start_processing)
        self.worker.transcript_signal.connect(self.transcript_panel.add_text)
        self.worker.verse_detected_signal.connect(self.approval_panel.queue_verse)
        self.worker.status_signal.connect(self._status_bar.showMessage)
        self.worker.error_signal.connect(lambda msg: logger.error(f"Worker Error: {msg}"))
        
        # Audio meter wiring
        self.worker.audio_capture.audio_level.connect(self.audio_meter.set_level)
        
        self.worker_thread.start()
        self._start_btn.setText("■ STOP")
        self._start_btn.setStyleSheet(f"background-color: {COLORS['danger']};")

    def stop_worker(self):
        """Gracefully stops the worker thread."""
        if self.worker:
            self.worker.stop_processing()
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self._start_btn.setText("▶ START")
        self._start_btn.setStyleSheet("")
        self._status_bar.showMessage("Transcription Stopped")

    @pyqtSlot(int)
    def update_startup_progress(self, val: int):
        """Updates the status bar with loading percentage."""
        self._status_bar.showMessage(f"Initializing Semantic AI: {val}%")

    @pyqtSlot(object, object, list)
    def on_models_ready(self, model, matrix, refs):
        """Called when background thread finishes loading embeddings."""
        self._status_bar.showMessage("AI Engine Ready.", 5000)
        self.manual_lookup.enable_semantic_mode(model, matrix, refs)
        # Store for future worker starts
        self._ai_model = model
        self._ai_matrix = matrix
        self._ai_refs = refs
        # Enable in active worker if running
        if self.worker:
            self.worker.enable_detection(model, matrix, refs)
