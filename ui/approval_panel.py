# ui/approval_panel.py

"""
A panel for operators to approve, dismiss, or edit detected scripture verses.
Emits signals for approved, dismissed, and edited verses.
Includes a switch for manual or automatic approval mode.
"""

import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QSizePolicy, QFrame, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from configparser import ConfigParser # For accessing config.ini

logger = logging.getLogger(__name__)

class ApprovalPanel(QWidget):
    """
    A panel for operators to approve, dismiss, or edit detected scripture verses.
    Emits signals for approved, dismissed, and edited verses.
    Includes a switch for manual or automatic approval mode, where auto-mode
    bypasses manual interaction and automatically sends verses to display.
    """
    verse_approved_signal = pyqtSignal(str, str, str) # text, reference, translation
    verse_dismissed_signal = pyqtSignal()
    edit_requested_signal = pyqtSignal(str, str, str) # text, reference, confidence_score

    def __init__(self, config: ConfigParser, parent=None):
        """
        Initializes the ApprovalPanel.

        Args:
            config (ConfigParser): The application configuration object.
            parent (QWidget): The parent widget, if any.
        """
        super().__init__(parent)
        self.setObjectName("approvalPanel")
        self.config = config
        self.current_verse_text = ""
        self.current_reference = ""
        self.current_confidence = 0.0
        self.default_translation = self.config.get('detection', 'default_translation', fallback='KJV')

        self.is_auto_approve_mode = False # Default to manual approval

        # Auto-send Timer (T-50)
        self.auto_send_timer = QTimer(self)
        self.auto_send_timer.setSingleShot(True)
        self.auto_send_timer.timeout.connect(self._on_approve_clicked)

        self._init_ui()
        self.clear_proposal() # Start in a clean state
        logger.info("ApprovalPanel initialized.")

    def _init_ui(self):
        """
        Sets up the user interface for the approval panel.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Auto/Manual Switch
        mode_layout = QHBoxLayout()
        self.auto_approve_checkbox = QCheckBox("Auto-Approve Mode", self)
        self.auto_approve_checkbox.setObjectName("autoApproveCheckbox")
        self.auto_approve_checkbox.stateChanged.connect(self._on_auto_approve_mode_changed)
        mode_layout.addStretch(1)
        mode_layout.addWidget(self.auto_approve_checkbox)
        main_layout.addLayout(mode_layout)

        # Frame for detected verse details
        details_frame = QFrame(self)
        details_frame.setObjectName("approvalDetailsFrame")
        details_frame.setFrameShape(QFrame.Shape.StyledPanel)
        details_frame.setFrameShadow(QFrame.Shadow.Raised)
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(5)

        self.verse_label = QLabel("No verse detected yet.", self)
        self.verse_label.setObjectName("approvalVerseLabel")
        self.verse_label.setWordWrap(True)
        self.verse_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verse_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #f0f0f0;")
        self.verse_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.reference_confidence_label = QLabel("", self)
        self.reference_confidence_label.setObjectName("approvalReferenceConfidenceLabel")
        self.reference_confidence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reference_confidence_label.setStyleSheet("font-size: 12pt; color: #aaaaaa;")

        details_layout.addWidget(self.verse_label)
        details_layout.addWidget(self.reference_confidence_label)
        main_layout.addWidget(details_frame)

        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.approve_button = QPushButton("Approve", self)
        self.approve_button.setObjectName("approveButton")
        self.approve_button.clicked.connect(self._on_approve_clicked)
        self.approve_button.setStyleSheet("background-color: #28a745; color: white;") # Green

        self.edit_button = QPushButton("Edit", self)
        self.edit_button.setObjectName("editButton")
        self.edit_button.clicked.connect(self._on_edit_clicked)
        self.edit_button.setStyleSheet("background-color: #007bff; color: white;") # Blue

        self.dismiss_button = QPushButton("Dismiss", self)
        self.dismiss_button.setObjectName("dismissButton")
        self.dismiss_button.clicked.connect(self._on_dismiss_clicked)
        self.dismiss_button.setStyleSheet("background-color: #dc3545; color: white;") # Red

        button_layout.addWidget(self.approve_button)
        button_layout.addWidget(self.edit_button)
        button_layout.addWidget(self.dismiss_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def _on_auto_approve_mode_changed(self, state):
        """
        Handles the change in the auto-approve checkbox state.
        """
        self.is_auto_approve_mode = (state == Qt.CheckState.Checked.value)
        logger.info(f"Auto-Approve Mode set to: {self.is_auto_approve_mode}")
        self._update_button_states()
        # If switching to auto-approve mode and there's a pending proposal, approve it
        if self.is_auto_approve_mode and self.current_verse_text:
            self._auto_approve_current_proposal()

    def _update_button_states(self):
        """
        Updates the enabled/disabled state of approval buttons based on mode and proposal status.
        """
        buttons_enabled = not self.is_auto_approve_mode and bool(self.current_verse_text)
        self.approve_button.setEnabled(buttons_enabled)
        self.edit_button.setEnabled(buttons_enabled)
        self.dismiss_button.setEnabled(buttons_enabled)

    def update_proposal(self, verse_text: str, reference: str, confidence: float):
        """
        Updates the panel with a new verse proposal.
        If in auto-approve mode, the verse is immediately approved.

        Args:
            verse_text (str): The detected verse text.
            reference (str): The detected verse reference (e.g., "John 3:16").
            confidence (float): The confidence score of the detection.
        """
        self.current_verse_text = verse_text
        self.current_reference = reference
        self.current_confidence = confidence

        self.verse_label.setText(verse_text)
        self.reference_confidence_label.setText(
            f"Reference: {reference} | Confidence: {confidence:.2f}"
        )
        logger.info(f"Updated proposal: {reference} (Confidence: {confidence:.2f})")

        if self.is_auto_approve_mode:
            self._auto_approve_current_proposal()
        else:
            self._update_button_states()
            # Start auto-send timer if enabled (T-50)
            auto_send = self.config.getboolean('detection', 'auto_send_enabled', fallback=False)
            if auto_send:
                delay_ms = self.config.getint('detection', 'auto_send_delay_seconds', fallback=3) * 1000
                logger.debug(f"Starting auto-send timer for {delay_ms}ms")
                self.auto_send_timer.start(delay_ms)

    def _auto_approve_current_proposal(self):
        """
        Automatically approves the current proposal if in auto-approve mode.
        """
        if self.current_verse_text and self.current_reference:
            logger.debug(f"Auto-approving verse: {self.current_reference}")
            self.verse_approved_signal.emit(
                self.current_verse_text,
                self.current_reference,
                self.default_translation
            )
            self.clear_proposal()
        else:
            logger.warning("Auto-approve attempted with no valid proposal.")

    def clear_proposal(self):
        """
        Clears the displayed verse proposal and disables action buttons
        (unless in auto-approve mode, where buttons are always disabled).
        """
        self.auto_send_timer.stop() # Stop any running timer (T-50)
        self.current_verse_text = ""
        self.current_reference = ""
        self.current_confidence = 0.0

        self.verse_label.setText("No verse detected yet.")
        self.reference_confidence_label.setText("")
        self._update_button_states() # Update button states based on cleared proposal and mode
        logger.info("Proposal cleared.")

    def _on_approve_clicked(self):
        """
        Handles the "Approve" button click. Emits verse_approved_signal.
        Only callable in manual mode.
        """
        if self.current_verse_text and self.current_reference and not self.is_auto_approve_mode:
            logger.debug(f"Manually approving verse: {self.current_reference}")
            self.auto_send_timer.stop() # Ensure timer is stopped if manual approval happens
            self.verse_approved_signal.emit(
                self.current_verse_text,
                self.current_reference,
                self.default_translation
            )
            self.clear_proposal()
        elif self.is_auto_approve_mode:
            logger.warning("Manual approve clicked while in auto-approve mode. Action ignored.")
        else:
            logger.warning("Approve clicked with no valid proposal.")

    def _on_dismiss_clicked(self):
        """
        Handles the "Dismiss" button click. Emits verse_dismissed_signal.
        Only callable in manual mode.
        """
        if not self.is_auto_approve_mode:
            logger.debug("Manually dismissing verse proposal.")
            self.auto_send_timer.stop() # Stop timer if manually dismissed (T-50)
            self.verse_dismissed_signal.emit()
            self.clear_proposal()
        else:
            logger.warning("Manual dismiss clicked while in auto-approve mode. Action ignored.")

    def _on_edit_clicked(self):
        """
        Handles the "Edit" button click. Emits edit_requested_signal.
        Only callable in manual mode.
        """
        if not self.is_auto_approve_mode:
            logger.debug(f"Edit requested for verse: {self.current_reference}")
            self.auto_send_timer.stop() # Stop timer if editing
            self.edit_requested_signal.emit(
                self.current_verse_text,
                self.current_reference,
                str(self.current_confidence)
            )
        else:
            logger.warning("Manual edit clicked while in auto-approve mode. Action ignored.")


if __name__ == '__main__':
    # Standalone test for ApprovalPanel
    import sys
    from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    from PyQt6.QtCore import QTimer

    # Mock ConfigParser for testing
    class MockConfig:
        def get(self, section, option, fallback=None):
            if section == 'detection' and option == 'default_translation':
                return 'KJV'
            return fallback
        def getboolean(self, section, option, fallback=False):
            if section == 'detection' and option == 'auto_send_enabled':
                return True # Test with auto_send_enabled
            return fallback
        def getint(self, section, option, fallback=0):
            if section == 'detection' and option == 'auto_send_delay_seconds':
                return 2 # Test with 2 second delay
            return fallback


    app = QApplication(sys.argv)
    main_window = QMainWindow()
    main_window.setWindowTitle("Approval Panel Test")
    main_window.setGeometry(100, 100, 700, 400)

    mock_config = MockConfig()
    approval_panel = ApprovalPanel(mock_config)

    central_widget = QWidget()
    central_layout = QVBoxLayout(central_widget)
    central_layout.addWidget(approval_panel)
    main_window.setCentralWidget(central_widget)

    # Test signal connections
    def on_verse_approved(text, ref, trans):
        print(f"Verse Approved: Text='{text}', Ref='{ref}', Trans='{trans}'")
    approval_panel.verse_approved_signal.connect(on_verse_approved)

    def on_verse_dismissed():
        print("Verse Dismissed!")
    approval_panel.verse_dismissed_signal.connect(on_verse_dismissed)

    def on_edit_requested(text, ref, conf):
        print(f"Edit Requested: Text='{text}', Ref='{ref}', Confidence='{conf}'")
    approval_panel.edit_requested_signal.connect(on_edit_requested)

    # Simulate a verse detection after a delay
    # This should auto-approve after 2 seconds
    QTimer.singleShot(1000, lambda: approval_panel.update_proposal(
        "For God so loved the world, that he gave his only begotten Son, that whosoever believeth in him should not perish, but have everlasting life.",
        "John 3:16",
        0.95
    ))

    main_window.show()
    sys.exit(app.exec())
