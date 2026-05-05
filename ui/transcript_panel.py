# ui/transcript_panel.py

"""
A widget to display a live, auto-scrolling transcription feed.
Text updates should be sent via the append_transcript_signal for thread safety.
"""

import logging
from PyQt6.QtWidgets import QWidget, QTextEdit, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt

logger = logging.getLogger(__name__)

class TranscriptPanel(QWidget):
    """
    A widget to display a live, auto-scrolling transcription feed.
    Text updates should be sent via the append_transcript_signal for thread safety.
    """
    append_transcript_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Initializes the TranscriptPanel.

        Args:
            parent (QWidget): The parent widget, if any.
        """
        super().__init__(parent)
        self.setObjectName("transcriptPanel")
        self._init_ui()
        self.append_transcript_signal.connect(self._append_transcript_threaded)
        logger.info("TranscriptPanel initialized.")

    def _init_ui(self):
        """
        Sets up the user interface for the transcript panel.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.transcript_display = QTextEdit(self)
        self.transcript_display.setObjectName("transcriptDisplay")
        self.transcript_display.setReadOnly(True)
        self.transcript_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-size: 14pt; border: none; padding: 5px;")
        # Ensure scrollbar is always visible or auto, not hidden
        self.transcript_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.transcript_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # No horizontal scroll

        layout.addWidget(self.transcript_display)
        self.setLayout(layout)

    def append_transcript(self, text: str):
        """
        Public method to append new text to the transcript display.
        This method should be called from any thread. It emits a signal
        to ensure the actual UI update happens in the main (UI) thread.

        Args:
            text (str): The new text to append.
        """
        if text:
            logger.debug(f"Received transcript text to append: '{text}'")
            self.append_transcript_signal.emit(text)

    def _append_transcript_threaded(self, text: str):
        """
        Slot method connected to append_transcript_signal.
        Appends text to the QTextEdit and auto-scrolls to the bottom.
        This method runs in the main (UI) thread.

        Args:
            text (str): The text to append.
        """
        self.transcript_display.append(text)
        # Auto-scroll to the bottom
        scrollbar = self.transcript_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        logger.debug(f"Appended text to transcript display and scrolled: '{text}'")

if __name__ == '__main__':
    # Standalone test for TranscriptPanel
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton
    from PyQt6.QtCore import QTimer, QThread, QObject

    # Simple Worker Thread to simulate text generation
    class Worker(QObject):
        new_text_signal = pyqtSignal(str)

        def run(self):
            messages = [
                "The quick brown fox jumps over the lazy dog.",
                "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
                "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
            ]
            for i, msg in enumerate(messages):
                QThread.msleep(1000) # Simulate work
                self.new_text_signal.emit(f"Line {i+1}: {msg}")
            QThread.msleep(2000)
            self.new_text_signal.emit("--- End of Simulation ---")

    app = QApplication(sys.argv)
    main_window = QMainWindow()
    main_window.setWindowTitle("Transcript Panel Test")
    main_window.setGeometry(100, 100, 600, 400)

    # Apply a minimal stylesheet for testing purposes if ui/styles.py isn't loaded
    app.setStyleSheet("""
        QMainWindow { background-color: #2b2b2b; }
        QTextEdit { background-color: #1e1e1e; color: #d4d4d4; }
        QPushButton { background-color: #3a3a3a; color: #f0f0f0; border: 1px solid #5a5a5a; }
    """)

    transcript_panel = TranscriptPanel()
    main_window.setCentralWidget(transcript_panel)

    # Simulate sending text from a background thread
    worker_thread = QThread()
    worker = Worker()
    worker.moveToThread(worker_thread)
    worker_thread.started.connect(worker.run)
    worker.new_text_signal.connect(transcript_panel.append_transcript) # Connect worker signal to panel's public method

    def start_simulation():
        worker_thread.start()
        print("Worker thread started. Simulating text generation...")

    # Start simulation after a short delay
    QTimer.singleShot(1000, start_simulation)

    main_window.show()
    sys.exit(app.exec())
