# tests/test_scripture_display.py
from ui.scripture_display import ScriptureDisplay

def test_scripture_display_content(qtbot, test_config):
    display = ScriptureDisplay(test_config)
    qtbot.addWidget(display)
    display.show_verse("John 3:16 text", "John 3:16", "KJV")
    assert display._verse_label.text() == "John 3:16 text"
    assert display._ref_label.text() == "John 3:16"
