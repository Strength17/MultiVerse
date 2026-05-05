# ui/scripture_display.py
import logging
import configparser
from PyQt6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QApplication
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QScreen

logger = logging.getLogger(__name__)

class ScriptureDisplay(QMainWindow):
    """
    Standalone fullscreen scripture display window.
    Designed for output to a projector or second monitor.
    """

    def __init__(self):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        self._setup_ui()
        self._apply_config()
        self._setup_animations()
        
        # Initial state is hidden (cleared)
        self.setWindowOpacity(0.0)
        self._is_ready = False

    def _setup_ui(self):
        """Initialize UI widgets and layout."""
        self.setWindowTitle("MultiVerse Display")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setContentsMargins(50, 50, 50, 50)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        
        self.verse_label = QLabel("")
        self.verse_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verse_label.setWordWrap(True)
        
        self.ref_label = QLabel("")
        self.ref_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.content_layout.addWidget(self.verse_label)
        self.content_layout.addSpacing(20)
        self.content_layout.addWidget(self.ref_label)
        
        self.layout.addWidget(self.content_widget)
        
        self.setObjectName("ScriptureDisplay")

    def _apply_config(self):
        """Apply styles and screen targeting from config.ini."""
        bg_color = self.config.get('display', 'background_color', fallback='#000000')
        self.setStyleSheet(f"background-color: {bg_color};")
        
        verse_color = self.config.get('display', 'verse_text_color', fallback='#FFFFFF')
        ref_color = self.config.get('display', 'reference_color', fallback='#AAAAAA')
        trans_color = self.config.get('display', 'translation_color', fallback='#888888')
        
        v_size = self.config.getint('display', 'verse_font_size', fallback=48)
        r_size = self.config.getint('display', 'reference_font_size', fallback=24)
        
        self.verse_label.setStyleSheet(f"color: {verse_color}; font-size: {v_size}px; font-weight: bold;")
        self.ref_label.setStyleSheet(f"color: {ref_color}; font-size: {r_size}px;")
        
        # Screen targeting
        target_idx = self.config.getint('display', 'target_screen_index', fallback=0)
        screens = QApplication.screens()
        
        if target_idx < len(screens):
            screen = screens[target_idx]
        else:
            logger.warning(f"Target screen index {target_idx} out of range. Falling back to primary screen.")
            screen = screens[0]
            
        self.setGeometry(screen.geometry())
        
        if self.config.getboolean('display', 'always_on_top', fallback=True):
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

    def _setup_animations(self):
        """Setup fade animations."""
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_duration = self.config.getint('display', 'fade_duration_ms', fallback=500)
        self.fade_anim.setDuration(self.fade_duration)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    @pyqtSlot(str, str, str)
    def show_verse(self, text: str, reference: str, translation: str):
        """Display a verse with a fade-in effect."""
        logger.info(f"Displaying verse: {reference} ({translation})")
        
        # If already showing something, fade out first or just update and fade in
        # For MVP, we'll update text and trigger fade in
        self.verse_label.setText(f'"{text}"')
        self.ref_label.setText(f"— {reference} ({translation})")
        
        self.fade_anim.stop()
        self.fade_anim.setStartValue(self.windowOpacity())
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()
        
        self.showFullScreen()
        self._is_ready = True

    @pyqtSlot()
    def clear_verse(self):
        """Clear the current verse with a fade-out effect."""
        logger.info("Clearing display")
        self.fade_anim.stop()
        self.fade_anim.setStartValue(self.windowOpacity())
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.start()

    def display_ready(self) -> bool:
        """Returns True if the display window is initialized and visible."""
        return self.isVisible() and self.windowOpacity() > 0
