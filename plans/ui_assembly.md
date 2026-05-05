# Implementation Plan - Task T-45 & UI Panel Fixes

## Objective
Correct `ui/history_panel.py` and `ui/manual_lookup.py` (which currently contain plan text) and implement `ui/main_window.py` to assemble the full operator UI.

## Key Files & Context
- `ui/history_panel.py`: Needs full implementation (currently a plan).
- `ui/manual_lookup.py`: Needs full implementation (currently a plan).
- `ui/main_window.py`: Needs full implementation (currently a plan).
- `ui/transcript_panel.py`: Already implemented, to be integrated.
- `ui/approval_panel.py`: Already implemented, to be integrated.
- `ui/settings_dialog.py`: Already implemented, to be integrated.
- `core/bible_db.py`: Needed for manual lookup functionality.

## Proposed Changes

### 1. Implement `ui/history_panel.py`
- Create `HistoryPanel` class inheriting from `QWidget`.
- Use a `QTextEdit` (read-only) for the log.
- Implement `add_history_entry(reference: str)` with a thread-safe signal.
- Format entries with timestamps: `[HH:MM:SS] Reference`.

### 2. Implement `ui/manual_lookup.py`
- Create `ManualLookupPanel` class inheriting from `QWidget`.
- Add `QLineEdit` for reference input, `QPushButton` for "Lookup", `QTextEdit` for result display, and `QPushButton` for "Send to Display".
- Implement signals: `lookup_requested_signal(str)` and `send_to_display_signal(str, str, str)`.
- Use `display_verse_result(text, ref)` to update the display after a DB query.

### 3. Implement `ui/main_window.py` (Task T-45)
- Create `MainWindow` class inheriting from `QMainWindow`.
- Set up a central widget with a layout containing two vertical splitters:
    - Left: `TranscriptPanel` and `HistoryPanel`.
    - Right: `ApprovalPanel` and `ManualLookupPanel`.
- Create a Menu Bar with "File" -> "Settings" and "Exit".
- Establish signal/slot connections:
    - `ApprovalPanel.verse_approved_signal` -> `ScriptureDisplayWindow.show_verse` and `HistoryPanel.add_history_entry`.
    - `ManualLookupPanel.lookup_requested_signal` -> `MainWindow._handle_manual_lookup` (which calls `bible_db`).
    - `ManualLookupPanel.send_to_display_signal` -> `ScriptureDisplayWindow.show_verse` and `HistoryPanel.add_history_entry`.
    - `SettingsAction` -> `SettingsDialog`.
- Apply `DARK_THEME_STYLESHEET` from `ui/styles.py`.

## Verification Plan

### Automated Tests
- Run `python ui/history_panel.py` (self-test block).
- Run `python ui/manual_lookup.py` (self-test block).
- Run `python ui/main_window.py` (self-test block with mocks).

### Manual Verification
- Verify layout looks correct (dark theme, splitters functional).
- Verify "File -> Settings" opens the dialog.
- Verify manual lookup triggers the mock DB and updates the result.
- Verify "Send to Display" and "Approve" (in mock mode) print to console and add to history.
