# MultiVerse — NDI Output & Bible Library Setup

## 1. NDI output (connect to vMix)

**What changed:** MultiVerse now broadcasts the current verse as a real
NDI video source (Route A from the original plan — a Python sender using
`cyndilib`, driven directly by the existing detection events). No capture
window, no third-party screen-grab tool.

**Install (once, on the machine running MultiVerse):**

1. Install the free **NDI Runtime** — download from https://ndi.video/tools/
   (pick "NDI Tools" or just the standalone "NDI Runtime" if offered).
   This installs `Processing.NDI.Lib.x64.dll`, which `cyndilib` needs at
   runtime — `pip` alone cannot provide it.
2. In the MultiVerse folder:
   ```
   pip install -r requirements_winrt.txt --break-system-packages
   ```
   (this now includes `cyndilib` and `pillow`).
3. Start MultiVerse as usual (`Start MultiVerse.bat` or `python server.py`).
   You'll see in the terminal:
   ```
   NDI sender 'MultiVerse' started (1920x1080 @ 3.0fps)
   ```
   If instead you see a warning about NDI being unavailable, re-check
   steps 1–2 — everything else in the app still runs fine either way.

**In vMix:**

1. **Add Input → NDI**
2. The source named `MultiVerse` (same name as `config/config.ini`'s
   `[ndi] sender_name`) appears automatically — same network, no IP
   entry needed.
3. Add it to a layer/overlay channel like any other input.

It updates automatically whenever a verse auto-displays in the app, and
blanks itself when you go off-air (`set_on_air(False)` / the OSC
"hide" command).

**Every visual setting is config-driven** — edit `config/config.ini`
`[ndi]` and restart, no code changes:
`width`, `height`, `fps`, `font_path`, `font_size`, `text_color`,
`background_color`, `background_alpha` (0 = transparent, for chroma-key
setups), `margin`.

**If it's not working:** the terminal log always says why (missing
`cyndilib`, or NDI Runtime not found) — that message is the fix.

---

## 2. Bible version library (multi-version, multi-language)

**Folder layout** — drop files in, no restart needed for them to be
detected (auto re-scans every 30s, and on every UI connect):

```
data/
  NKJV/
    English/NKJV.sqlite3
    French/LSG.sqlite3        <- any language folder name works
  ASV/
    English/ASV.sqlite3
```

- A version with no language subfolder (just `data/ASV/ASV.sqlite3`) is
  treated as English-only automatically.
- The old flat layout (`data/NKJV.SQLite3` directly in `data/`) still
  works too, for backward compatibility.

**In the UI:**

- The version dropdown (top of the "Suggestions" column, and mirrored in
  the new **⚙ Settings** tab at the bottom) lists every detected
  version/language automatically. Picking one rebuilds the detection
  index in the background — the mic and transcript keep running while
  it happens (a few seconds for a large translation).
- If a version has a second language folder next to the active one
  (e.g. French next to NKJV/English), a toggle appears in **Settings**:
  *"Also show French translation underneath, when available."* When on,
  every detected verse shows the secondary-language text underneath the
  primary one, on the live stage and in the NDI output. When a version
  has no second language, the toggle is simply hidden — nothing to
  configure.

**Defaults** live in `config/config.ini` `[library]`:
`data_root` (folder to scan), `show_secondary_translation_by_default`,
`rescan_interval_seconds`.

---

## 3. Everything else that changed this session

- `config/config.ini` documents (and code now actually reads) every
  detection threshold — no hardcoded numbers left in `vector_search.py`,
  `detection_orchestrator.py`, or `verse_detector.py`. Tune behavior by
  editing the file, not the code.
- `min_overlap_ratio` (hard gate) and `dedup_seconds` (same-verse
  re-fire suppression) fix the two remaining false-positive/double-fire
  issues from the Genesis 9:15 case.
- Transcript panel now reads top-to-bottom chronologically with a
  timestamp on the left, and auto-scrolls to the newest line unless
  you've manually scrolled up to review history.
