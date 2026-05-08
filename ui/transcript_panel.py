# ui/transcript_panel.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextCursor, QTextCharFormat, QColor
from ui.styles import COLORS, FONTS

class TranscriptPanel(QWidget):
    """Displays rolling live transcript with inline verse highlights."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_primary']};
                font-family: {FONTS['family_mono']};
                font-size: {FONTS['size_sm']}px;
                border: none;
            }}
        """)
        layout.addWidget(self._text_edit)
        
    def add_text(self, text: str, timestamp: float = 0.0) -> None:
        """Compatibility method for transcription worker."""
        self.append_segment(text, timestamp)

    def append_segment(self, text: str, timestamp: float) -> None:
        """Appends a new transcription segment. Auto-scrolls."""
        mins = int(timestamp // 60)
        secs = int(timestamp % 60)
        ts = f"[{mins:02d}:{secs:02d}]"
        
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Timestamp in muted color
        fmt_ts = QTextCharFormat()
        fmt_ts.setForeground(QColor(COLORS["text_muted"]))
        cursor.setCharFormat(fmt_ts)
        cursor.insertText(f" {ts} ")
        
        # Segment text in primary color
        fmt_text = QTextCharFormat()
        fmt_text.setForeground(QColor(COLORS["text_primary"]))
        cursor.setCharFormat(fmt_text)
        cursor.insertText(text + "\n")
        
        # Always scroll to bottom
        self._text_edit.verticalScrollBar().setValue(
            self._text_edit.verticalScrollBar().maximum()
        )
    
    def highlight_match(self, phrase: str) -> None:
        """Highlights the most recently matched phrase in amber."""
        # Search backward from end, highlight last occurrence of phrase
        document = self._text_edit.document()
        cursor = document.find(
            phrase,
            self._text_edit.textCursor().position() - len(phrase) * 4,
            QTextDocument.FindFlag.FindBackward
        )
        if not cursor.isNull():
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(COLORS["warning"] + "40"))  # 25% opacity
            fmt.setForeground(QColor(COLORS["warning"]))
            cursor.setCharFormat(fmt)
