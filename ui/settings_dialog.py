# ui/settings_dialog.py

import logging
from configparser import ConfigParser, ExtendedInterpolation
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTabWidget, QWidget,
    QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QFileDialog,
    QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator, QDoubleValidator

logger = logging.getLogger(__name__)

class SettingsDialog(QDialog):
    """
    A dialog window to view and modify application settings from config.ini.
    Settings are grouped by sections in tabs.
    """
    settings_saved = pyqtSignal() # Signal emitted after settings are successfully saved

    def __init__(self, config_path: str, parent=None):
        """
        Initializes the SettingsDialog.

        Args:
            config_path (str): The path to the config.ini file.
            parent (QWidget): The parent widget, if any.
        """
        super().__init__(parent)
        self.setObjectName("settingsDialog")
        self.setWindowTitle("MultiVerse Settings")
        self.config_path = config_path
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.widgets = {} # Stores references to created input widgets

        self._load_config()
        self._init_ui()
        logger.info("SettingsDialog initialized.")

    def _load_config(self):
        """
        Loads settings from the config.ini file.
        """
        try:
            self.config.read(self.config_path)
            logger.info(f"Loaded configuration from: {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading config.ini from {self.config_path}: {e}")
            QMessageBox.critical(self, "Configuration Error",
                                 f"Failed to load configuration file:\n{self.config_path}\nError: {e}")
            self.reject() # Close the dialog if config fails to load

    def _init_ui(self):
        """
        Builds the UI dynamically based on the loaded configuration.
        """
        main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget(self)
        self.tab_widget.setObjectName("settingsTabWidget")
        main_layout.addWidget(self.tab_widget)

        for section in self.config.sections():
            section_widget = QWidget()
            section_layout = QFormLayout(section_widget)
            section_layout.setContentsMargins(10, 10, 10, 10)
            self.widgets[section] = {}

            for option, value in self.config.items(section):
                label = QLabel(option.replace('_', ' ').title() + ":", section_widget)
                input_widget = self._create_input_widget(section, option, value)
                section_layout.addRow(label, input_widget)
                self.widgets[section][option] = input_widget
            self.tab_widget.addTab(section_widget, section.title())

        # Buttons
        button_layout = QHBoxLayout()
        self.apply_button = QPushButton("Apply", self)
        self.apply_button.setObjectName("applyButton")
        self.apply_button.clicked.connect(self._on_apply_clicked)
        self.apply_button.setStyleSheet("background-color: #28a745; color: white;") # Green

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setObjectName("cancelButton")
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.cancel_button.setStyleSheet("background-color: #dc3545; color: white;") # Red

        button_layout.addStretch(1)
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)
        self.setMinimumSize(400, 300)

    def _create_input_widget(self, section: str, option: str, value: str):
        """
        Creates and returns an appropriate input widget based on the config option's value.
        """
        widget = None
        # Try to determine type
        if value.lower() in ['true', 'false']:
            widget = QCheckBox(self)
            widget.setChecked(value.lower() == 'true')
        else:
            try:
                int(value)
                widget = QSpinBox(self)
                widget.setRange(-99999, 99999) # Reasonable default range
                widget.setValue(int(value))
            except ValueError:
                try:
                    float(value)
                    widget = QDoubleSpinBox(self)
                    widget.setRange(-99999.0, 99999.0)
                    widget.setSingleStep(0.1)
                    widget.setValue(float(value))
                except ValueError:
                    # Default to QLineEdit for strings
                    widget = QLineEdit(self)
                    widget.setText(value)
                    if option == 'model_dir' and section == 'transcription':
                        browse_button = QPushButton("Browse...", self)
                        browse_button.clicked.connect(
                            lambda: self._browse_directory(widget)
                        )
                        h_layout = QHBoxLayout()
                        h_layout.addWidget(widget)
                        h_layout.addWidget(browse_button)
                        container = QWidget(self)
                        container.setLayout(h_layout)
                        return container # Return the container for model_dir


        if widget is None: # Fallback in case none of the above matched
            widget = QLineEdit(self)
            widget.setText(value)
        return widget

    def _browse_directory(self, line_edit: QLineEdit):
        """
        Opens a directory dialog for selecting a path.
        """
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", line_edit.text())
        if directory:
            line_edit.setText(directory)
            logger.debug(f"Selected directory: {directory}")

    def _on_apply_clicked(self):
        """
        Validates inputs, saves changes back to config.ini, and accepts the dialog.
        """
        logger.info("Apply button clicked. Attempting to save settings.")
        new_config_values = ConfigParser(interpolation=ExtendedInterpolation())
        new_config_values.read_dict(self.config) # Start with existing config

        try:
            for section, options_widgets in self.widgets.items():
                for option, widget in options_widgets.items():
                    # Handle composite widgets (like QLineEdit + Browse button)
                    if isinstance(widget, QWidget) and isinstance(widget.layout(), QHBoxLayout):
                        actual_widget = widget.layout().itemAt(0).widget()
                        if isinstance(actual_widget, QLineEdit):
                            value = actual_widget.text()
                        else:
                            raise TypeError(f"Unhandled composite widget type for {section}.{option}")
                    elif isinstance(widget, QLineEdit):
                        value = widget.text()
                    elif isinstance(widget, QSpinBox):
                        value = str(widget.value())
                    elif isinstance(widget, QDoubleSpinBox):
                        value = str(widget.value())
                    elif isinstance(widget, QCheckBox):
                        value = str(widget.isChecked()).lower()
                    else:
                        logger.warning(f"Unhandled widget type for {section}.{option}: {type(widget)}")
                        continue

                    # Basic validation - more advanced validation can be added here
                    if not value:
                        if section == 'transcription' and option == 'initial_prompt':
                            # initial_prompt can be empty
                            new_config_values.set(section, option, value)
                        else:
                            QMessageBox.warning(self, "Validation Error",
                                                f"'{option.replace('_', ' ').title()}' in '{section.title()}' cannot be empty.")
                            return # Don't save, wait for user correction
                    else:
                        # Attempt to cast to original type for basic validation
                        original_value = self.config.get(section, option)
                        if original_value.lower() in ['true', 'false']:
                            if value.lower() not in ['true', 'false']:
                                QMessageBox.warning(self, "Validation Error",
                                                    f"'{option.replace('_', ' ').title()}' in '{section.title()}' must be 'true' or 'false'.")
                                return
                        elif original_value.isdigit() or (original_value.startswith('-') and original_value[1:].isdigit()):
                            try:
                                int(value)
                            except ValueError:
                                QMessageBox.warning(self, "Validation Error",
                                                    f"'{option.replace('_', ' ').title()}' in '{section.title()}' must be an integer.")
                                return
                        elif '.' in original_value and all(part.isdigit() for part in original_value.split('.', 1)):
                            try:
                                float(value)
                            except ValueError:
                                QMessageBox.warning(self, "Validation Error",
                                                    f"'{option.replace('_', ' ').title()}' in '{section.title()}' must be a number.")
                                return

                        new_config_values.set(section, option, value)

            # Write to config file
            with open(self.config_path, 'w') as configfile:
                new_config_values.write(configfile)
            self.config = new_config_values # Update internal config
            self.settings_saved.emit() # Emit signal that settings were saved
            logger.info("Settings saved successfully.")
            self.accept() # Close dialog

        except Exception as e:
            logger.error(f"Error saving config.ini: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save settings:\n{e}")

    def _on_cancel_clicked(self):
        """
        Closes the dialog without saving changes.
        """
        logger.info("Cancel button clicked. Discarding changes.")
        self.reject() # Close dialog
