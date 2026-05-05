# tests/test_scripture_display.py
import pytest
from PyQt6.QtWidgets import QApplication
from ui.scripture_display import ScriptureDisplay

@pytest.fixture
def app(qtbot):
    """Fixture for QApplication."""
    # QApplication is handled by pytest-qt
    pass

@pytest.fixture
def display(qtbot):
    """Fixture for ScriptureDisplay widget."""
    widget = ScriptureDisplay()
    qtbot.addWidget(widget)
    return widget

def test_display_initial_state(display):
    """Verify initial state of the display window."""
    assert display.windowTitle() == "MultiVerse Display"
    assert display.verse_label.text() == ""
    assert display.ref_label.text() == ""
    assert display.windowOpacity() == 0.0

def test_show_verse(display, qtbot):
    """Verify showing a verse updates labels and starts fade."""
    display.show_verse("In the beginning", "Genesis 1:1", "KJV")
    
    assert "In the beginning" in display.verse_label.text()
    assert "Genesis 1:1" in display.ref_label.text()
    assert "KJV" in display.ref_label.text()
    
    # Check if animation is running or opacity is increasing
    # Since it's an animation, we might need to wait or check end value
    assert display.fade_anim.state() == display.fade_anim.State.Running
    assert display.fade_anim.endValue() == 1.0

def test_clear_verse(display, qtbot):
    """Verify clearing a verse starts fade out."""
    display.show_verse("Text", "Ref", "Trans")
    display.clear_verse()
    
    assert display.fade_anim.state() == display.fade_anim.State.Running
    assert display.fade_anim.endValue() == 0.0

def test_display_ready(display):
    """Verify display_ready logic."""
    # Initially not ready because opacity is 0
    assert display.display_ready() is False
    
    # Show verse and set opacity manually for test
    display.show_verse("Text", "Ref", "Trans")
    display.setWindowOpacity(1.0)
    assert display.display_ready() is True
