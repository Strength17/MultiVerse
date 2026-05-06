# tests/test_full_system.py
import pytest
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow
from ui.scripture_display import ScriptureDisplay
from core.bible_db import BibleDB

def test_full_system_workflow(qtbot, test_config, db_conn, mock_embeddings):
    """Integration test simulating a full user session."""
    # 1. Startup
    main_window = MainWindow(test_config, db_conn)
    qtbot.addWidget(main_window)
    display_window = ScriptureDisplay(test_config)
    qtbot.addWidget(display_window)
    
    # Wiring (simulating main.py logic)
    main_window.on_models_ready(None, *mock_embeddings)
    
    # 2. Manual Search & Display
    qtbot.keyClicks(main_window.manual_lookup._search_input, "beginning")
    qtbot.wait(300) # Wait for debounce
    
    # Select first result
    assert main_window.manual_lookup._results_list.count() > 0
    item = main_window.manual_lookup._results_list.item(0)
    
    # Double click to send
    with qtbot.waitSignal(main_window.manual_lookup.send_to_display):
        main_window.manual_lookup._on_item_double_clicked(item)
    
    # 3. Verify Display
    # Simulate signal connection usually done in main or controller
    data = item.data(Qt.ItemDataRole.UserRole)
    display_window.show_verse(data["verse"], data["reference"])
    
    assert display_window._verse_label.text() is not None
    assert display_window.isVisible()
    
    # 4. Transcription & Approval (Simulation)
    detection = {
        "verse_text": "Jesus wept",
        "reference": "John 11:35",
        "confidence": 0.99,
        "method": "reference"
    }
    main_window.approval_panel.show_detection(detection)
    assert main_window.approval_panel._empty_label.isHidden()
    
    # Click SEND
    with qtbot.waitSignal(main_window.approval_panel.verse_sent):
        qtbot.mouseClick(main_window.approval_panel.findChild(pytest.importorskip("PyQt6.QtWidgets").QPushButton, "btn_success"), Qt.MouseButton.LeftButton)
    
    # 5. Clear Display
    display_window.clear_display()
    qtbot.wait(600) # Wait for fade animation
    assert display_window.windowOpacity() < 1.0
