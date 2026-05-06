# tests/test_transcript_panel.py
from ui.transcript_panel import TranscriptPanel

def test_transcript_append(qtbot):
    panel = TranscriptPanel()
    qtbot.addWidget(panel)
    panel.append_segment("Hello world", 1.0)
    assert "Hello world" in panel._text_edit.toPlainText()

def test_transcript_timestamp(qtbot):
    panel = TranscriptPanel()
    qtbot.addWidget(panel)
    panel.append_segment("Test", 65.0)
    assert "[01:05]" in panel._text_edit.toPlainText()
