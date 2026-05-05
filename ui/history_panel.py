# ui/history_panel.py

"""
A widget to display a scrollable log of all verses sent to the scripture display.
Entries can be added safely from any thread via the add_history_entry method.
"""

import logging
from datetime import datetime
from PyQt6.QtWidgets import QWidget, QTextEdit, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt

logger = logging.getLogger(__name__)

class HistoryPanel(QWidget):
    """
    A widget to display a scrollable log of all verses sent to the scripture display.
    Entries can be added safely from any thread via the add_history_entry method.
    """
    add_history_entry_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Initializes the HistoryPanel.

        Args:
            parent (QWidget): The parent widget, if any.
        """
        super().__init__(parent)
        self.setObjectName("historyPanel")
        self._init_ui()
        self.add_history_entry_signal.connect(self._add_history_entry_threaded)
        logger.info("HistoryPanel initialized.")

    def _init_ui(self):
        """
        Sets up the user interface for the history panel.
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.history_display = QTextEdit(self)
        self.history_display.setObjectName("historyDisplay")
        self.history_display.setReadOnly(True)
        self.history_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-size: 10pt; border: none; padding: 5px;")
        self.history_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.history_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        layout.addWidget(self.history_display)
        self.setLayout(layout)

    def add_history_entry(self, reference: str):
        """
        Public method to add a new verse reference to the history log.
        This method can be called from any thread. It emits a signal
        to ensure the actual UI update happens in the main (UI) thread.

        Args:
            reference (str): The verse reference (e.g., "John 3:16").
        """
        if reference:
            timestamp = datetime.now().strftime("%H:%M:%S")
            entry = f"[{timestamp}] {reference}"
            logger.debug(f"Received history entry to add: '{entry}'")
            self.add_history_entry_signal.emit(entry)

    def _add_history_entry_threaded(self, entry: str):
        """
        Slot method connected to add_history_entry_signal.
        Appends the entry to the QTextEdit and auto-scrolls to the bottom.
        This method runs in the main (UI) thread.

        Args:
            entry (str): The formatted history entry string.
        """
        self.history_display.append(entry)
        scrollbar = self.history_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        logger.debug(f"Appended history entry and scrolled: '{entry}'")

    def clear_history(self):
        """
        Clears all entries from the history log.
        """
        self.history_display.clear()
        logger.info("History log cleared.")


if __name__ == '__main__':
    # Standalone test for HistoryPanel
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
    from PyQt6.QtCore import QTimer

    app = QApplication(sys.argv)
    main_window = QMainWindow()
    main_window.setWindowTitle("History Panel Test")
    main_window.setGeometry(100, 100, 400, 600)

    # Apply a minimal stylesheet for testing purposes
    app.setStyleSheet("""
        QMainWindow { background-color: #2b2b2b; }
        QTextEdit { background-color: #1e1e1e; color: #d4d4d4; }
        QPushButton { background-color: #3a3a3a; color: #f0f0f0; border: 1px solid #5a5a5a; }
    """)

    history_panel = HistoryPanel()

    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    central_layout.addWidget(history_panel)

    test_button = QPushButton("Add Test Entry")
    test_button.clicked.connect(lambda: history_panel.add_history_entry(
        f"Test Verse {datetime.now().second}: Test Chapter {datetime.now().minute}"
    ))
    central_layout.addWidget(test_button)

    clear_button = QPushButton("Clear History")
    clear_button.clicked.connect(history_panel.clear_history)
    central_layout.addWidget(clear_button)


    main_window.setCentralWidget(central_widget)

    # Simulate adding entries over time
    QTimer.singleShot(1000, lambda: history_panel.add_history_entry("John 3:16"))
    QTimer.singleShot(2500, lambda: history_panel.add_history_entry("Psalm 23:1"))
    QTimer.singleShot(4000, lambda: history_panel.add_history_entry("Romans 8:28"))
    QTimer.singleShot(5500, lambda: history_panel.add_history_entry("Philippians 4:13"))

    main_window.show()
    sys.exit(app.exec())
