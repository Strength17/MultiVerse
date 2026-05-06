# ui/audio_meter.py

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QColor
from ui.styles import COLORS

class AudioMeterWidget(QWidget):
    """Displays real-time audio input level as animated vertical bars.
    
    Receives RMS float (0.0–1.0) via set_level(). Animates with decay.
    """
    
    BAR_COUNT = 20
    BAR_GAP = 2
    DECAY_RATE = 0.08   # How fast bars fall after peak (per repaint tick)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0         # Current RMS level 0.0–1.0
        self._display_level = 0.0 # Smoothed display level (with decay)
        self._peak = 0.0          # Peak hold value
        self._peak_hold_frames = 0
        
        # 60fps repaint timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60fps
        
        self.setMinimumHeight(48)
        self.setMinimumWidth(120)
    
    def set_level(self, rms: float) -> None:
        """Receive new RMS value from audio thread. Thread-safe via Qt signal."""
        # Scale up for visibility
        self._level = min(1.0, rms * 3.0)
    
    def _tick(self) -> None:
        """Called every ~16ms. Applies decay and schedules repaint."""
        if self._level > self._display_level:
            self._display_level = self._level
            self._peak = self._level
            self._peak_hold_frames = 30  # Hold peak for 30 frames (~0.5s)
        else:
            self._display_level = max(0.0, self._display_level - self.DECAY_RATE)
        
        if self._peak_hold_frames > 0:
            self._peak_hold_frames -= 1
        else:
            self._peak = max(0.0, self._peak - self.DECAY_RATE * 0.5)
        
        # Reset level for next window
        self._level = 0.0
        self.update()  # Schedule repaint
    
    def paintEvent(self, event) -> None:
        """Draw bars using QPainter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        bar_width = (w - (self.BAR_COUNT - 1) * self.BAR_GAP) / self.BAR_COUNT
        lit_bars = int(self._display_level * self.BAR_COUNT)
        
        for i in range(self.BAR_COUNT):
            x = int(i * (bar_width + self.BAR_GAP))
            
            if i < lit_bars:
                fraction = i / self.BAR_COUNT
                if fraction < 0.6:
                    color = QColor(COLORS["meter_low"])
                elif fraction < 0.85:
                    color = QColor(COLORS["meter_mid"])
                else:
                    color = QColor(COLORS["meter_high"])
            else:
                color = QColor(COLORS["meter_bg"])
            
            painter.fillRect(int(x), 0, int(bar_width), h, color)
        
        painter.end()
