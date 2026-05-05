# ui/main_window.py

import logging
from configparser import ConfigParser, ExtendedInterpolation
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QStatusBar, QApplication, QMessageBox, QFileDialog, QLabel,
    QComboBox, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from datetime import datetime
import sounddevice as sd

# Import all UI panels
from ui.transcript_panel import TranscriptPanel
from ui.approval_panel import ApprovalPanel
from ui.history_panel import HistoryPanel
from ui.manual_lookup import ManualLookupPanel
from ui.settings_dialog import SettingsDialog
from ui.styles import DARK_THEME_STYLESHEET

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """
    The main application window, assembling all UI panels and managing their interactions.
    """
    session_started = pyqtSignal()
    session_stopped = pyqtSignal()

    def __init__(self, config: ConfigParser, scripture_display_window, bible_db, parent=None):
        """
        Initializes the MainWindow.

        Args:
            config (ConfigParser): The application configuration object.
            scripture_display_window: Reference to the ScriptureDisplayWindow instance.
            bible_db: Reference to the BibleDB instance for verse lookups.
            parent (QWidget): The parent widget, if any.
        """
        super().__init__(parent)
        self.setObjectName("mainWindow")
        self.setWindowTitle("MultiVerse Operator Console")
        self.config = config
        self.scripture_display_window = scripture_display_window
        self.bible_db = bible_db

        self._init_ui()
        self._create_connections()
        self._apply_theme()
        logger.info("MainWindow initialized.")

    def _init_ui(self):
        """
        Sets up the main window layout, menu bar, and status bar.
        Instantiates and arranges all child panels.
        """
        self.setMinimumSize(1024, 768)

        self._create_menu_bar()
        self.setStatusBar(QStatusBar(self))
        self.statusBar().setObjectName("mainStatusBar")
        
        # Audio Device Selector
        self.statusBar().addWidget(QLabel(" Audio:", self))
        self.device_selector = QComboBox(self)
        self.device_selector.setObjectName("deviceSelector")
        self.device_selector.setMinimumWidth(150)
        self._populate_audio_devices()
        self.device_selector.currentIndexChanged.connect(self._on_device_changed)
        self.statusBar().addWidget(self.device_selector)

        self.statusBar().addSeparator()

        # Translation Selector
        self.statusBar().addWidget(QLabel(" Trans:", self))
        self.translation_selector = QComboBox(self)
        self.translation_selector.setObjectName("translationSelector")
        self.translation_selector.addItem("KJV")
        self.translation_selector.setEnabled(False) # KJV only in MVP
        self.statusBar().addWidget(self.translation_selector)

        self.statusBar().addSeparator()

        # Clear Display Button
        self.clear_display_button = QPushButton("Clear Display", self)
        self.clear_display_button.setObjectName("clearDisplayButton")
        self.clear_display_button.setStyleSheet("background-color: #6c757d; color: white; padding: 2px 10px;")
        self.clear_display_button.clicked.connect(self.scripture_display_window.clear_verse)
        self.statusBar().addWidget(self.clear_display_button)

        self.statusBar().addSeparator()

        # Display Status Indicator
        self.display_status_label = QLabel("Display: Offline", self)
        self.display_status_label.setObjectName("displayStatusLabel")
        self.display_status_label.setStyleSheet("color: #dc3545; font-weight: bold; margin-right: 10px;")
        self.statusBar().addPermanentWidget(self.display_status_label)
        
        self.statusBar().showMessage("Ready")

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # Left Splitter (Transcript and History)
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        left_splitter.setObjectName("leftSplitter")

        self.transcript_panel = TranscriptPanel(self)
        left_splitter.addWidget(self.transcript_panel)

        self.history_panel = HistoryPanel(self)
        left_splitter.addWidget(self.history_panel)
        left_splitter.setStretchFactor(0, 3) # Give more space to transcript
        left_splitter.setStretchFactor(1, 1)

        # Right Splitter (Approval and Manual Lookup)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setObjectName("rightSplitter")

        self.approval_panel = ApprovalPanel(self.config, self)
        right_splitter.addWidget(self.approval_panel)

        self.manual_lookup_panel = ManualLookupPanel(self.config, self)
        right_splitter.addWidget(self.manual_lookup_panel)
        right_splitter.setStretchFactor(0, 2) # Give more space to approval
        right_splitter.setStretchFactor(1, 1)

        main_layout.addWidget(left_splitter)
        main_layout.addWidget(right_splitter)

        # Status Check Timer
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._check_display_status)
        self.status_timer.start(2000) # Check every 2 seconds

    def _populate_audio_devices(self):
        """
        Queries available audio input devices using sounddevice and populates the dropdown.
        """
        try:
            devices = sd.query_devices()
            default_index = self.config.getint('audio', 'input_device_index', fallback=0)
            
            self.device_selector.clear()
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    name = f"{i}: {dev['name']}"
                    self.device_selector.addItem(name, i)
            
            # Select current device from config
            index = self.device_selector.findData(default_index)
            if index != -1:
                self.device_selector.setCurrentIndex(index)
            
        except Exception as e:
            logger.error(f"Error populating audio devices: {e}")
            self.device_selector.addItem("Error loading devices", -1)

    def _on_device_changed(self, index):
        """
        Handles audio device selection change.
        """
        device_id = self.device_selector.itemData(index)
        if device_id is not None and device_id != -1:
            logger.info(f"Audio device changed to: {device_id}")
            self.config.set('audio', 'input_device_index', str(device_id))
            self.statusBar().showMessage(f"Audio device set to {device_id}", 3000)

    def _check_display_status(self):
        """
        Checks if the scripture display window is open and visible.
        Updates the status label accordingly.
        """
        try:
            is_ready = False
            if hasattr(self.scripture_display_window, 'display_ready'):
                is_ready = self.scripture_display_window.display_ready()
            elif hasattr(self.scripture_display_window, 'isVisible'):
                is_ready = self.scripture_display_window.isVisible()

            if is_ready:
                self.display_status_label.setText("Display: Online")
                self.display_status_label.setStyleSheet("color: #28a745; font-weight: bold; margin-right: 10px;")
            else:
                self.display_status_label.setText("Display: Offline")
                self.display_status_label.setStyleSheet("color: #dc3545; font-weight: bold; margin-right: 10px;")
        except Exception as e:
            logger.error(f"Error checking display status: {e}")
            self.display_status_label.setText("Display: Error")
            self.display_status_label.setStyleSheet("color: #ffc107; font-weight: bold; margin-right: 10px;")

    def _create_menu_bar(self):
        """
        Creates the application's menu bar and actions.
        """
        menu_bar = self.menuBar()
        menu_bar.setObjectName("mainMenuBar")

        # File Menu
        file_menu = menu_bar.addMenu("&File")
        file_menu.setObjectName("fileMenu")

        settings_action = QAction("&Settings...", self)
        settings_action.setObjectName("settingsAction")
        settings_action.setShortcut("Ctrl+Shift+S")
        settings_action.setStatusTip("Open application settings")
        settings_action.triggered.connect(self._open_settings_dialog)
        file_menu.addAction(settings_action)

        export_action = QAction("&Export Session...", self)
        export_action.setObjectName("exportAction")
        export_action.setShortcut("Ctrl+E")
        export_action.setStatusTip("Export transcript and history to a text file")
        export_action.triggered.connect(self._export_session)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setObjectName("exitAction")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(exit_action)

        # Session Menu
        session_menu = menu_bar.addMenu("&Session")
        session_menu.setObjectName("sessionMenu")

        self.start_session_action = QAction("&Start Session", self)
        self.start_session_action.setShortcut("F5")
        self.start_session_action.triggered.connect(self._on_start_session)
        session_menu.addAction(self.start_session_action)

        self.stop_session_action = QAction("S&top Session", self)
        self.stop_session_action.setShortcut("F6")
        self.stop_session_action.setEnabled(False)
        self.stop_session_action.triggered.connect(self._on_stop_session)
        session_menu.addAction(self.stop_session_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        help_menu.setObjectName("helpMenu")
        about_action = QAction("&About", self)
        about_action.triggered.connect(lambda: QMessageBox.information(self, "About MultiVerse", "MultiVerse v1.0\nReal-time scripture detection and display."))
        help_menu.addAction(about_action)

    def _create_connections(self):
        """
        Establishes signal-slot connections between panels and core logic.
        """
        # ApprovalPanel -> ScriptureDisplayWindow & HistoryPanel
        self.approval_panel.verse_approved_signal.connect(
            self.scripture_display_window.show_verse
        )
        self.approval_panel.verse_approved_signal.connect(
            lambda text, ref, trans: self.history_panel.add_history_entry(ref)
        )
        self.approval_panel.verse_dismissed_signal.connect(
            lambda: self.statusBar().showMessage("Verse proposal dismissed.")
        )

        # ManualLookupPanel -> BibleDB & ScriptureDisplayWindow & HistoryPanel
        self.manual_lookup_panel.lookup_requested_signal.connect(self._handle_manual_lookup)
        self.manual_lookup_panel.send_to_display_signal.connect(
            self.scripture_display_window.show_verse
        )
        self.manual_lookup_panel.send_to_display_signal.connect(
            lambda text, ref, trans: self.history_panel.add_history_entry(ref)
        )

    def _open_settings_dialog(self):
        """
        Opens the SettingsDialog.
        """
        # SettingsDialog takes config_path. Assuming self.config.path is set by main.py
        config_path = getattr(self.config, 'path', 'config.ini')
        settings_dialog = SettingsDialog(config_path, self)
        settings_dialog.settings_saved.connect(self._reapply_settings)
        settings_dialog.exec()

    def _handle_manual_lookup(self, reference_string: str):
        """
        Performs a Bible verse lookup using the BibleDB and updates the manual lookup panel.
        """
        try:
            verse_text, canonical_reference = self.bible_db.lookup_verse(reference_string)
            self.manual_lookup_panel.display_verse_result(verse_text, canonical_reference)
            if verse_text:
                self.statusBar().showMessage(f"Manual lookup successful for {canonical_reference}")
            else:
                self.statusBar().showMessage(f"Manual lookup failed: {reference_string} not found.")
        except Exception as e:
            logger.error(f"Error during manual lookup: {e}")
            self.statusBar().showMessage("Error during lookup.")

    def _export_session(self):
        """
        Gathers transcript and history and opens a file dialog to export.
        """
        from utils.session_export import export_session_log
        
        transcript = self.transcript_panel.transcript_display.toPlainText()
        # History entries are formatted strings in the QTextEdit
        history_text = self.history_panel.history_display.toPlainText()
        history = [h.strip() for h in history_text.split('\n') if h.strip()]

        default_filename = f"MultiVerse_Session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Session Log", default_filename, "Text Files (*.txt);;All Files (*)"
        )

        if file_path:
            success = export_session_log(transcript, history, file_path)
            if success:
                QMessageBox.information(self, "Export Successful", f"Session log saved to:\n{file_path}")
            else:
                QMessageBox.critical(self, "Export Failed", "An error occurred while saving the session log.")

    def _on_start_session(self):
        """Handles session start request."""
        self.start_session_action.setEnabled(False)
        self.stop_session_action.setEnabled(True)
        self.session_started.emit()
        self.statusBar().showMessage("Session starting...")

    def _on_stop_session(self):
        """Handles session stop request."""
        self.start_session_action.setEnabled(True)
        self.stop_session_action.setEnabled(False)
        self.session_stopped.emit()
        self.statusBar().showMessage("Session stopped.")

    def _reapply_settings(self):
        """
        Re-reads configuration and applies relevant settings to UI components.
        """
        logger.info("Re-applying settings after config save.")
        config_path = getattr(self.config, 'path', 'config.ini')
        new_config = ConfigParser(interpolation=ExtendedInterpolation())
        new_config.read(config_path)
        self.config = new_config

        # Update panels that need config refresh
        self.approval_panel.config = self.config
        self.approval_panel.default_translation = self.config.get('detection', 'default_translation', fallback='KJV')
        self.manual_lookup_panel.config = self.config
        self.manual_lookup_panel.default_translation = self.config.get('detection', 'default_translation', fallback='KJV')

        # Refresh audio devices list
        self._populate_audio_devices()

        self.statusBar().showMessage("Settings applied. Some changes may require a restart.")

    def _apply_theme(self):
        """
        Applies the global stylesheet to the application.
        """
        QApplication.instance().setStyleSheet(DARK_THEME_STYLESHEET)
        logger.debug("Dark theme stylesheet applied.")


if __name__ == '__main__':
    import sys
    import os

    # Mock BibleDB
    class MockBibleDB:
        def lookup_verse(self, reference: str):
            if "John 3:16" in reference:
                return "For God so loved the world...", "John 3:16"
            return None, None

    # Mock ScriptureDisplayWindow
    class MockScriptureDisplayWindow(QObject):
        def show_verse(self, text, ref, trans):
            print(f"DISPLAY: {ref} - {text} ({trans})")
        def clear_verse(self):
            print("DISPLAY: Cleared")

    app = QApplication(sys.argv)
    
    config = ConfigParser()
    config.read_dict({
        'audio': {'input_device_index': '0'},
        'detection': {'default_translation': 'KJV'},
        'ui': {'theme': 'dark'}
    })
    config.path = 'config.ini'

    main_window = MainWindow(config, MockScriptureDisplayWindow(), MockBibleDB())
    main_window.show()
    sys.exit(app.exec())
