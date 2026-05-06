# tests/test_approval_panel.py
from ui.approval_panel import ApprovalPanel

def test_approval_panel_reset(qtbot):
    panel = ApprovalPanel()
    qtbot.addWidget(panel)
    panel.show_detection({"verse_text": "Text", "reference": "Ref", "confidence": 0.9})
    panel._reset()
    assert not panel._empty_label.isHidden()

def test_approval_panel_signals(qtbot):
    panel = ApprovalPanel()
    qtbot.addWidget(panel)
    detection = {"verse_text": "Text", "reference": "Ref", "confidence": 0.9}
    panel.show_detection(detection)
    with qtbot.waitSignal(panel.verse_sent) as blocker:
        panel._on_send()
    assert blocker.args[0] == detection
