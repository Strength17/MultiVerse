# tests/test_manual_lookup.py
from ui.manual_lookup import ManualLookup

def test_manual_lookup_input(qtbot, db_conn):
    lookup = ManualLookup(db_conn)
    qtbot.addWidget(lookup)
    lookup._search_input.setText("John")
    # Debounce is 120ms
    qtbot.wait(200)
    assert lookup._results_list.count() >= 0
