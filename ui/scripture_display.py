# ui/scripture_display.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from ui.styles import COLORS, FONTS

class ScriptureDisplay(QWidget):
    """Fullscreen scripture display window with fade effects."""

    def __init__(self, config):
        super().__init__()
        self._config = config
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet(f"background-color: {self._config['display']['background_color']};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._trans_label = QLabel()
        self._trans_label.setStyleSheet(f"color: {COLORS['text_trans']}; font-size: {FONTS['size_trans']}px;")
        self._trans_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._trans_label)
        
        self._verse_label = QLabel()
        self._verse_label.setWordWrap(True)
        self._verse_label.setStyleSheet(f"color: {COLORS['text_verse']}; font-size: {FONTS['size_verse']}px; font-weight: bold;")
        self._verse_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._verse_label)
        
        self._ref_label = QLabel()
        self._ref_label.setStyleSheet(f"color: {COLORS['text_ref']}; font-size: {FONTS['size_ref']}px;")
        self._ref_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._ref_label)
        
        self._anim = None

    def show_verse(self, text: str, reference: str, translation: str = "KJV") -> None:
        """Fades in new verse."""
        self._verse_label.setText(text)
        self._ref_label.setText(reference)
        self._trans_label.setText(translation)
        self._fade_in()

    def _fade_in(self) -> None:
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(int(self._config["display"]["fade_in_ms"]))
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.show()
        self._anim.start()

    def clear_display(self) -> None:
        """Fades out."""
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(int(self._config["display"]["fade_out_ms"]))
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.hide)
        self._anim.start()

    def move_to_monitor(self, index: int) -> None:
        """Moves window to target monitor."""
        screens = QApplication.screens()
        target = screens[index] if index < len(screens) else screens[0]
        geo = target.geometry()
        self.setGeometry(geo)
        if self._config.getboolean("display", "fullscreen"):
            self.showFullScreen()
