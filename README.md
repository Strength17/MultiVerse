# Window Verse — Windows-Native STT Build

Speech-to-text now comes entirely from Windows 11's own on-device dictation
engine (WinRT `SpeechRecognizer`, continuous DICTATION mode) — no Whisper,
no downloaded model file, no GPU/CPU load for transcription. Everything
downstream (verse detection, semantic fallback, narrative tracking, OSC,
UI) is unchanged from what you already had.

**Confirmed vs. unconfirmed, going in:**
- Confirmed (Microsoft docs, checked live): the WinRT dictation API is real
  and the Python bindings (`pywinrt`) support Python 3.13 on Windows 11.
- **Not yet confirmed for your specific setup:** whether the *free dictation*
  topic constraint runs fully offline on your machine, as opposed to closed
  command lists (which Microsoft explicitly documents as on-device). You
  said you tested "voice typing" offline — but Win+H voice typing and this
  WinRT dictation API are two different things, and Microsoft's own
  documentation states Win+H routes through Azure by default. Step 1 below
  settles this for your machine, definitively, before anything else depends
  on it.

## Step 1 — Verify it's actually offline on your machine

Turn Wi-Fi/Ethernet **fully off** (not just no signal — disable the
adapter, or use Airplane Mode). Then:

```
python verify_offline_stt.py
```

Speak a few sentences, including a book name like "Deuteronomy." You should
see `OK: no network reachable` at the top, live `[hyp]` lines as you talk,
and `[FINAL]` lines at each pause. If it fails to compile or produces no
text while genuinely offline, stop here — the rest of this bundle assumes
Step 1 passes.

## Step 2 — Install dependencies and drop in your data files

```
pip install -r requirements_winrt.txt --break-system-packages
```

Copy your existing `NKJV.SQLite3`, `bible_vectors.index`, and
`bible_verse_map.pkl` into the `data/` folder (same files you already have
— see `data/README_DATA.txt`). You do **not** need `ggml-small.en.bin`
anymore; that was the old Whisper model and nothing in this build loads it.

## Step 3 — Run it and test end-to-end

```
python server.py
```

Open `ui/index.html` in a browser, click **Start**, and speak a verse
reference out loud ("John chapter 3 verse 16"). You should see it appear in
the left transcript panel within roughly a second, and the verse card
should render on match. The terminal also prints `[TRANSCRIPT] ...` and a
JSON line on every detection — that's your ground-truth log if the UI and
what you actually said ever disagree.

---

## How reference detection works (verse_detector.py + reference_context.py)

Every transcript chunk is run through a priority-ordered list of patterns
in `detect_direct_reference()`. First match wins. In priority order:

| # | Spoken form | Result |
|---|---|---|
| 1 | `"John 3:16"` | Immediate trigger, 97% confidence |
| 2 | `"John chapter 3 verses 16 through 18"` | Immediate trigger, verse range |
| 3 | `"Romans chapter 8 verse 28"` or `"...and verse 28"` | Immediate trigger, 95% |
| 3b | `"Psalm 23 verse 1"` (no "chapter" keyword) | Immediate trigger, 95% |
| 4 | `"James chapter 4"` | Confirms book+chapter context, no trigger yet |
| 4b | `"turn to Romans"` | Primes book only — chapter still unknown |
| 4c | `"chapter 8"` (no book) | Fills in chapter for an already-primed book |
| 5 | `"verses 16 to 18"` (no book/chapter) | Resolved against confirmed context |
| 6 | `"Jude 3"` — **single-chapter book** | Immediate trigger: Jude 1:3 (unambiguous — only one chapter exists) |
| 7 | `"John 11"` — **multi-chapter book, bare number** | **PRIMES a pending guess only — does not trigger.** Ambiguous between "chapter 11" and "verse 11 of the current chapter." |
| 8 | `"verse 1"` (following #7) | **Confirms** the pending guess → John 11:1, 78% confidence (medium band) |
| 9 | `"john three sixteen"` | Immediate trigger, 92% |
| 10 | fuzzy (`"genisis"`, `"jon"`, etc.) | Immediate trigger, 78% |

**The pending-guess rule (#7/#8) is the fix for "John chapter 1 verse 1"
sometimes transcribing as "John 11":** a bare number right after a book
name is never assumed to be a chapter. It's held as a *guess* until one of
three things happens:
- a `"verse N"` arrives next → **confirmed** (medium-confidence, tagged
  `bare_number_confirmed: true` in the JSON output so the UI can flag it)
- an explicit full reference arrives instead → the guess is **discarded**
- ~60 seconds pass with nothing → the guess **falls back to chapter-only**
  (matches the "Book chapter N" convention) — it is never auto-promoted
  into a guessed verse number.

Single-chapter books (Obadiah, Philemon, 2 John, 3 John, Jude) skip all of
this — a bare number after those book names can *only* be a verse, so it
fires immediately.

Ordinal book prefixes ("First/Second/Third Corinthians") and their
cardinal STT-artifact equivalents ("One/Two/Three Corinthians") both
normalize to `1/2/3 Corinthians` before matching — scoped only to the
handful of book names that actually take a number prefix, so "one" / "two"
/ "three" elsewhere in a sentence are never touched.

## Out-of-range detection (bible_db.py)

On startup, `BibleDB` reads the ACTUAL max chapter-per-book and max
verse-per-chapter directly from your `.SQLite3` file (cached to
`data/range_cache.json` so this only re-scans when the file changes — same
convention as `data/schema_cache.json`). Every detected reference is
checked against these real numbers before the verse lookup runs.

If a chapter or verse is out of range, nothing renders silently — the
terminal prints a specific, actionable JSON warning naming the book's
actual last valid chapter/verse:

```json
{"warning": "reference_out_of_range", "book": "Romans", "chapter": 25,
 "verse": 1, "reason": "chapter_out_of_range", "requested_chapter": 25,
 "max_chapter": 16}
```

This is different from `matched_reference_missing_from_db` (the reference
IS in range, but the DB has no row for it — a data/schema problem, not a
speech-recognition problem). Both fail loud; neither fails silent.

---

### If Nebuchadnezzar/Deuteronomy-style mishears show up

They'll self-correct over time. `vocab_correction.py` fuzzy-matches spoken
text against your 66 canonical book names and remembers every correction it
makes in `data/corrections_learned.json` — same mishear, fixed instantly
next time, with zero extra setup from you.
