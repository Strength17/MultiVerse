"""
console_output.py

Single shared source of truth for whether the terminal's cursor is
currently sitting at the end of an in-place-overwritten "live" line (the
`\\r[live] ...` partial-transcript echo in server.py).

Without this, any OTHER print -- a finalized [TRANSCRIPT] line, a JSONL
detection line, a narrative-event line -- that fires while a live line is
open gets visually glued onto the end of it instead of starting on its own
line, since the live line never emitted its own trailing newline. The fix
is one flag, checked/cleared by every non-live print site before it writes:
if a live line is open, emit a newline first to close it out, THEN write.

Usage:
  mark_live_line_open()       -- call right after writing a `\\r[live] ...`
                                  in-place line (no trailing newline)
  write_line(text)            -- use for every OTHER terminal write instead
                                  of a bare print(); handles the flag itself
"""

from __future__ import annotations

import threading

_live_line_open = False
_lock = threading.Lock()


def mark_live_line_open() -> None:
    """Call this right after printing the in-place `\\r[live] ...` partial
    line. Records that the terminal cursor is parked mid-line so the next
    write_line() call knows to close it out first."""
    global _live_line_open
    with _lock:
        _live_line_open = True


def write_line(text: str) -> None:
    """Print a complete line to the terminal, safely, regardless of
    whether a live partial-transcript line is currently open. This is the
    ONLY way any of [TRANSCRIPT], JSONL detections, or narrative events
    should reach the terminal -- never a bare print(). Thread-safe: the
    transcript prints happen on the main event loop while detection JSONL
    prints happen on the background detection thread, so the flag can be
    touched from either."""
    global _live_line_open
    with _lock:
        needs_newline = _live_line_open
        _live_line_open = False
    if needs_newline:
        print()  # close out the open live line with its own newline
    print(text, flush=True)
