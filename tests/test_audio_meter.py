# tests/test_audio_meter.py
import pytest
from ui.audio_meter import AudioMeterWidget

def test_audio_meter_level_scaling(qtbot):
    widget = AudioMeterWidget()
    qtbot.addWidget(widget)
    widget.set_level(0.1)
    assert widget._level == pytest.approx(0.3) # Scaling rms * 3.0

def test_audio_meter_decay(qtbot):
    widget = AudioMeterWidget()
    qtbot.addWidget(widget)
    widget.set_level(1.0)
    widget._tick()
    level_after_peak = widget._display_level
    widget._tick()
    assert widget._display_level < level_after_peak
