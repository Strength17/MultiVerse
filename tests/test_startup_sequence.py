# tests/test_startup_sequence.py
import pytest
from main import main
from ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication

def test_main_window_instant_launch(qtbot, test_config, db_conn):
    # Setup
    window = MainWindow(test_config, db_conn)
    qtbot.addWidget(window)
    window.show()
    
    # Assert window is visible immediately
    assert window.isVisible()
    # Assert status bar shows initial message
    assert "Waking up AI engine..." in window._status_bar.currentMessage()

def test_startup_progress_update(qtbot, test_config, db_conn):
    window = MainWindow(test_config, db_conn)
    qtbot.addWidget(window)
    
    window.update_startup_progress(45)
    assert "45%" in window._status_bar.currentMessage()

def test_on_models_ready_transition(qtbot, test_config, db_conn, mock_embeddings):
    window = MainWindow(test_config, db_conn)
    qtbot.addWidget(window)
    
    matrix, refs = mock_embeddings
    # Mock model
    class MockModel:
        def encode(self, texts, **kwargs):
            import numpy as np
            return np.zeros((len(texts), 384))
            
    window.on_models_ready(MockModel(), matrix, refs)
    
    # Check status bar
    assert "AI Engine Ready." in window._status_bar.currentMessage()
    # Check lookup widget state
    assert "Semantic AI active" in window.manual_lookup._search_input.placeholderText()
    assert window.manual_lookup._model is not None
