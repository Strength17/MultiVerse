# ui/manual_lookup.py

"""
A widget allowing manual lookup of Bible verses and sending them to the display.
"""

import logging
from configparser import ConfigParser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
    QSizePolicy, QFrame
)
from PyQt6.QtCore import pyqtSignal, Qt

logger = logging.getLogger(__name__)

class ManualLookupPanel(QWidget):
    """
    A widget allowing manual lookup of Bible verses and sending them to the display.
    """
    lookup_requested_signal = pyqtSignal(str) # Emits the reference string to be looked up
    send_to_display_signal = pyqtSignal(str, str, str) # Emits verse_text, reference, translation

    def __init__(self, config: ConfigParser, parent=None):
        """
        Initializes the ManualLookupPanel.

        Args:
            config (ConfigParser): The application configuration object.
            parent (QWidget): The parent widget, if any.
        """
        super().__init__(parent)
        self.setObjectName("manualLookupPanel")
        self.config = config
        self.current_displayed_verse_text = ""
        self.current_displayed_reference = ""
        self.default_translation = self.config.get('detection', 'default_translation', fallback='KJV')

        self._init_ui()
        self._update_send_button_state()
        logger.info("ManualLookupPanel initialized.")

    def _init_ui(self):
        """
        Sets up the user interface for the manual lookup panel.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Input and Lookup Button
        input_layout = QHBoxLayout()
        self.reference_input = QLineEdit(self)
        self.reference_input.setObjectName("referenceInput")
        self.reference_input.setPlaceholderText("e.g., John 3:16 or Psalm 23")
        self.reference_input.returnPressed.connect(self._on_lookup_clicked) # Lookup on Enter key
        input_layout.addWidget(self.reference_input)

        self.lookup_button = QPushButton("Lookup", self)
        self.lookup_button.setObjectName("lookupButton")
        self.lookup_button.clicked.connect(self._on_lookup_clicked)
        input_layout.addWidget(self.lookup_button)
        main_layout.addLayout(input_layout)

        # Result Display Area
        self.result_display = QTextEdit(self)
        self.result_display.setObjectName("resultDisplay")
        self.result_display.setReadOnly(True)
        self.result_display.setPlaceholderText("Verse text will appear here after lookup.")
        self.result_display.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4; font-size: 12pt; border: none; padding: 5px;")
        self.result_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.result_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main_layout.addWidget(self.result_display)

        # Send to Display Button
        self.send_button = QPushButton("Send to Display", self)
        self.send_button.setObjectName("sendToDisplayButton")
        self.send_button.clicked.connect(self._on_send_to_display_clicked)
        self.send_button.setStyleSheet("background-color: #0078d7; color: white;") # Blue
        main_layout.addWidget(self.send_button)

        self.setLayout(main_layout)

    def _on_lookup_clicked(self):
        """
        Handles the "Lookup" button click or Enter key press.
        Emits lookup_requested_signal with the text from the input field.
        """
        reference_string = self.reference_input.text().strip()
        if reference_string:
            logger.info(f"Lookup requested for: '{reference_string}'")
            self.lookup_requested_signal.emit(reference_string)
        else:
            self.result_display.setText("Please enter a verse reference.")
            logger.warning("Lookup attempted with empty reference string.")
        self._update_send_button_state()

    def display_verse_result(self, verse_text: str, reference: str):
        """
        Public method to populate the result display area after a lookup.

        Args:
            verse_text (str): The verse text found.
            reference (str): The canonical reference (e.g., "John 3:16").
        """
        self.current_displayed_verse_text = verse_text
        self.current_displayed_reference = reference
        if verse_text and reference:
            self.result_display.setText(f"{verse_text}\n\n— {reference} ({self.default_translation})")
            logger.info(f"Displayed lookup result for: {reference}")
        else:
            self.result_display.setText("Verse not found. Please check the reference.")
            logger.warning(f"No verse found for reference: {self.reference_input.text()}")
            self.current_displayed_verse_text = ""
            self.current_displayed_reference = ""
        self._update_send_button_state()

    def _on_send_to_display_clicked(self):
        """
        Handles the "Send to Display" button click.
        Emits send_to_display_signal with the currently displayed verse.
        """
        if self.current_displayed_verse_text and self.current_displayed_reference:
            logger.info(f"Sending to display: {self.current_displayed_reference}")
            self.send_to_display_signal.emit(
                self.current_displayed_verse_text,
                self.current_displayed_reference,
                self.default_translation
            )
            self.clear_results()
        else:
            logger.warning("Send to Display clicked with no valid verse to send.")

    def clear_results(self):
        """
        Clears the input field and the result display area.
        """
        self.reference_input.clear()
        self.result_display.clear()
        self.current_displayed_verse_text = ""
        self.current_displayed_reference = ""
        self.result_display.setPlaceholderText("Verse text will appear here after lookup.")
        self._update_send_button_state()
        logger.info("Manual lookup results cleared.")

    def _update_send_button_state(self):
        """
        Enables/disables the 'Send to Display' button based on whether a verse is displayed.
        """
        self.send_button.setEnabled(bool(self.current_displayed_verse_text))


if __name__ == '__main__':
    # Standalone test for ManualLookupPanel
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    from PyQt6.QtCore import QTimer

    # Mock ConfigParser for testing
    class MockConfig:
        def get(self, section, option, fallback=None):
            if section == 'detection' and option == 'default_translation':
                return 'KJV'
            return fallback

    app = QApplication(sys.argv)
    main_window = QMainWindow()
    main_window.setWindowTitle("Manual Lookup Panel Test")
    main_window.setGeometry(100, 100, 600, 500)

    mock_config = MockConfig()
    manual_lookup_panel = ManualLookupPanel(mock_config)

    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    central_layout.addWidget(manual_lookup_panel)
    main_window.setCentralWidget(central_widget)

    # Mock functions to simulate external interactions
    def mock_lookup_db(reference_string: str):
        print(f"Mock DB Lookup for: {reference_string}")
        if "John 3:16" in reference_string:
            QTimer.singleShot(500, lambda: manual_lookup_panel.display_verse_result(
                "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.",
                "John 3:16"
            ))
        elif "Psalm 23" in reference_string:
            QTimer.singleShot(500, lambda: manual_lookup_panel.display_verse_result(
                "The Lord is my shepherd; I shall not want.\nHe maketh me to lie down in green pastures: he leadeth me beside the still waters.",
                "Psalm 23:1-2"
            ))
        else:
            QTimer.singleShot(500, lambda: manual_lookup_panel.display_verse_result("", ""))

    manual_lookup_panel.lookup_requested_signal.connect(mock_lookup_db)

    def mock_send_to_display(text, ref, trans):
        print(f"Mock Display: Sending Text='{text}', Ref='{ref}', Trans='{trans}'")
    manual_lookup_panel.send_to_display_signal.connect(mock_send_to_display)


    main_window.show()
    sys.exit(app.exec())
