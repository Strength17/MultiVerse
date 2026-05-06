# tests/test_integration_pipeline.py
import pytest
from PyQt6.QtCore import Qt, QTimer
from core.verse_detector import DetectionWorker
from ui.approval_panel import ApprovalPanel
from ui.scripture_display import ScriptureDisplay
from ui.manual_lookup import ManualLookup

def test_integration_detection_to_display(qtbot, test_config, mock_embeddings):
    # Setup
    matrix, refs = mock_embeddings
    worker = DetectionWorker(None, matrix, refs, test_config)
    approval = ApprovalPanel()
    display = ScriptureDisplay(test_config)
    qtbot.addWidget(approval)
    qtbot.addWidget(display)

    # Wiring
    worker.verse_detected.connect(approval.show_detection)
    approval.verse_sent.connect(lambda d: display.show_verse(d['verse_text'], d['reference']))

    # Trigger detection
    detection = {
        "verse_text": "For God so loved the world",
        "reference": "John 3:16",
        "confidence": 0.95,
        "method": "reference"
    }
    
    with qtbot.waitSignal(approval.verse_sent, timeout=1000):
        worker.verse_detected.emit(detection)
        qtbot.mouseClick(approval.findChild(pytest.importorskip("PyQt6.QtWidgets").QPushButton, "btn_success"), Qt.MouseButton.LeftButton)

    assert display._verse_label.text() == "For God so loved the world"
    assert display._ref_label.text() == "John 3:16"

def test_integration_search_to_display(qtbot, db_conn, test_config):
    lookup = ManualLookup(db_conn)
    display = ScriptureDisplay(test_config)
    qtbot.addWidget(lookup)
    qtbot.addWidget(display)

    # Wiring
    lookup.send_to_display.connect(lambda d: display.show_verse(d['verse_text'], d['reference']))

    # Simulate Search & Approval
    verse_data = {"verse_text": "In the beginning", "reference": "Gen 1:1", "translation": "KJV"}
    lookup.send_to_display.emit(verse_data)

    assert display._verse_label.text() == "In the beginning"
    assert display._ref_label.text() == "Gen 1:1"
