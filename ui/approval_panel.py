# ui/approval_panel.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from ui.styles import COLORS, FONTS, RADIUS

class ApprovalPanel(QWidget):
    """Detection-triggered approval UI with confidence badges and auto-timer."""
    verse_sent = pyqtSignal(dict)
    verse_dismissed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setStyleSheet(f"#card {{ border: 2px solid {COLORS['bg_elevated']}; }}")
        
        layout = QVBoxLayout(self)
        self._content_layout = QVBoxLayout()
        layout.addLayout(self._content_layout)
        
        self._empty_label = QLabel("Listening for scripture...")
        self._empty_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._empty_label)
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._auto_send)
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        layout.addWidget(self._progress)
        
        self._current_verse = None

    def queue_verse(self, detection: dict) -> None:
        """Compatibility method for transcription worker."""
        # Check config for auto-send settings
        self.show_detection(detection)

    def show_detection(self, detection: dict, auto_send=False, delay=5) -> None:
        """Displays detection card with amber glow."""
        self._current_verse = detection
        self.setStyleSheet(f"#card {{ border: 2px solid {COLORS['warning']}; }}")
        
        # Clear existing
        for i in reversed(range(self._content_layout.count())): 
            self._content_layout.itemAt(i).widget().setParent(None)
        self._empty_label.setVisible(False)
        
        # Method + confidence badge
        method = detection.get("method", "semantic")
        conf = int(detection.get("confidence", 0) * 100)
        badge = QLabel(f"{method.upper()} | {conf}%")
        badge.setStyleSheet(f"color: {COLORS['warning']}; font-size: {FONTS['size_xs']}px;")
        self._content_layout.addWidget(badge)
        
        # Verse text
        text = QLabel(detection.get("verse_text", ""))
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: {FONTS['size_lg']}px;")
        self._content_layout.addWidget(text)
        
        # Reference
        ref = QLabel(detection.get("reference", ""))
        ref.setStyleSheet(f"color: {COLORS['accent']}; font-size: {FONTS['size_md']}px;")
        self._content_layout.addWidget(ref)
        
        # Buttons
        btns = QHBoxLayout()
        send = QPushButton("✓ SEND")
        send.setObjectName("btn_success")
        send.clicked.connect(self._on_send)
        
        skip = QPushButton("✗ SKIP")
        skip.setObjectName("btn_danger")
        skip.clicked.connect(self._on_dismiss)
        
        edit = QPushButton("✏ EDIT")
        edit.setObjectName("btn_muted")
        
        btns.addWidget(send)
        btns.addWidget(skip)
        btns.addWidget(edit)
        self._content_layout.addLayout(btns)
        
        if auto_send:
            self._progress.setVisible(True)
            self._progress.setRange(0, delay * 10)
            self._progress.setValue(delay * 10)
            self._timer.start(100)

    def _on_send(self):
        self._timer.stop()
        self.verse_sent.emit(self._current_verse)
        self._reset()

    def _on_dismiss(self):
        self._timer.stop()
        self.verse_dismissed.emit()
        self._reset()

    def _auto_send(self):
        val = self._progress.value() - 1
        self._progress.setValue(val)
        if val <= 0:
            self._on_send()

    def _reset(self):
        for i in reversed(range(self._content_layout.count())): 
            item = self._content_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                # For nested layouts, we need to clear them too or just remove
                self._remove_layout(item.layout())
        self._empty_label.setVisible(True)
        self._progress.setVisible(False)
        self.setStyleSheet(f"#card {{ border: 2px solid {COLORS['bg_elevated']}; }}")

    def _remove_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._remove_layout(item.layout())
