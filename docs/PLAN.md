# PLAN.md
# MultiVerse — Complete UI Rebuild & Core Feature Implementation Plan
# For: Gemini via OpenCode
# Authority: This document overrides all previous workflow phases.
# The codebase exists on GitHub. This is a targeted rebuild, not a greenfield build.
# ─────────────────────────────────────────────────────────────────────────────

## MISSION STATEMENT

The existing code runs but the UI is broken and the core pipeline is non-functional.
This plan rebuilds the UI to professional EasyWorship-grade standards and implements
three non-negotiable features: real-time audio waveform, live transcription, and
fluid semantic scripture detection. Every task in this plan is precise, testable,
and ordered. Follow it exactly.

---

## PART 1 — DESIGN SYSTEM

### 1.1 Color Tokens

Define these ONCE in `ui/styles.py` as Python constants. Every widget reads from here.
Never hardcode a color string anywhere else.

```python
# ui/styles.py

COLORS = {
    # --- Backgrounds ---
    "bg_window":   "#0D0D0D",   # Root window background
    "bg_panel":    "#161616",   # Panel / sidebar background
    "bg_card":     "#1F1F1F",   # Cards, list items, input fields
    "bg_elevated": "#282828",   # Toolbars, headers, raised surfaces
    "bg_hover":    "#2E2E2E",   # Hover state for interactive items
    "bg_selected": "#1A3A5C",   # Selected item (deep blue tint)

    # --- Accent ---
    "accent":      "#4A9EFF",   # Primary blue — buttons, focus rings, highlights
    "accent_dark": "#1A6ECC",   # Pressed/active state
    "success":     "#22C55E",   # Live / approved / connected (green)
    "warning":     "#F59E0B",   # Detected / pending (amber)
    "danger":      "#EF4444",   # Dismiss / clear / error (red)
    "muted":       "#4B5563",   # Disabled / inactive

    # --- Text ---
    "text_primary":   "#F9FAFB",  # Body text
    "text_secondary": "#9CA3AF",  # Labels, meta
    "text_muted":     "#6B7280",  # Placeholders, timestamps
    "text_verse":     "#FFFFFF",  # Scripture verse text (display window)
    "text_ref":       "#B0C4DE",  # Reference (display window)
    "text_trans":     "#7B9BB8",  # Translation label (display window)

    # --- Borders ---
    "border":       "#2D2D2D",   # Standard separator
    "border_focus": "#4A9EFF",   # Focus ring

    # --- Audio Meter ---
    "meter_low":  "#22C55E",  # 0–60% RMS (green)
    "meter_mid":  "#F59E0B",  # 60–85% RMS (amber)
    "meter_high": "#EF4444",  # 85–100% RMS (red)
    "meter_bg":   "#1A1A1A",  # Meter background
}

FONTS = {
    "family": "Segoe UI",        # Windows primary; falls back to system sans-serif
    "family_mono": "Consolas",   # Monospace for transcript/debug output
    "size_xs":   10,
    "size_sm":   11,
    "size_md":   13,             # Default body
    "size_lg":   15,
    "size_xl":   20,
    "size_verse": 42,            # Scripture display window — verse body
    "size_ref":   24,            # Scripture display window — reference
    "size_trans": 16,            # Scripture display window — translation label
}

RADIUS = {
    "sm": 4,
    "md": 8,
    "lg": 12,
    "xl": 16,
}

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
}
```

### 1.2 QSS Master Stylesheet

Write the full QSS as one string in `ui/styles.py` → `def get_stylesheet() -> str`.
It must cover every widget class used in the app. Key rules:

```
QMainWindow, QWidget#central         → bg_window
QWidget#panel_left, #panel_center, #panel_right → bg_panel, border-right 1px border
QWidget#card                         → bg_card, border-radius radius_md
QLineEdit                            → bg_card, text_primary, border border, padding 8px,
                                       border-radius radius_sm
                                       :focus → border border_focus
QPushButton#btn_primary              → bg accent, text white, border-radius radius_sm,
                                       font-weight bold, padding 8px 16px
                                       :hover → bg accent_dark
                                       :pressed → slightly darker
QPushButton#btn_success              → bg success
QPushButton#btn_danger               → bg danger
QPushButton#btn_muted                → bg bg_elevated, text text_secondary
QListWidget                          → bg bg_card, border none, outline none
QListWidget::item                    → padding 8px 12px, color text_primary
QListWidget::item:selected           → bg bg_selected, color white
QListWidget::item:hover              → bg bg_hover
QScrollBar:vertical                  → bg bg_card, width 6px, no-buttons
QScrollBar::handle:vertical          → bg muted, border-radius 3px
QLabel#label_section                 → color text_secondary, font-size size_sm, uppercase
QLabel#label_verse                   → color text_primary, font-size size_lg, font-weight bold
QLabel#label_ref                     → color accent, font-size size_md
QSplitter::handle                    → bg border, width/height 1px
```

---

## PART 2 — MAIN WINDOW LAYOUT

File: `ui/main_window.py`  
Class: `MainWindow(QMainWindow)`

### 2.1 Structural Layout

```
┌────────────────────────────────────────────────────────────────────────┐
│  HEADER BAR (height: 52px, bg: bg_elevated)                            │
│  [● MultiVerse Logo/Name]  [Audio Device ▼]  [▶ START] [■ STOP]       │
│  [Spacer]  [🟢 Audio: Connected]  [🔵 Display: Ready]  [⚙ Settings]   │
├─────────────────────┬──────────────────────────┬───────────────────────┤
│  LEFT PANEL (30%)   │  CENTER PANEL (40%)       │  RIGHT PANEL (30%)   │
│  bg_panel           │  bg_window                │  bg_panel            │
│                     │                           │                      │
│  ┌───────────────┐  │  ┌─────────────────────┐  │  ┌────────────────┐  │
│  │ AUDIO METER   │  │  │  DETECTION CARD     │  │  │ VERSE HISTORY  │  │
│  │ (VU bars)     │  │  │                     │  │  │                │  │
│  └───────────────┘  │  │  Detected Verse Text│  │  │  Scrollable    │  │
│                     │  │  Reference + Conf % │  │  │  list of sent  │  │
│  ┌───────────────┐  │  │                     │  │  │  verses        │  │
│  │ LIVE          │  │  │  [✓ SEND] [✗ SKIP]  │  │  │                │  │
│  │ TRANSCRIPT    │  │  │  [✏ EDIT]           │  │  └────────────────┘  │
│  │               │  │  └─────────────────────┘  │                      │
│  │ Auto-scroll   │  │                           │                      │
│  │ dark text on  │  │  ┌─────────────────────┐  │                      │
│  │ bg_card       │  │  │  DISPLAY PREVIEW    │  │                      │
│  └───────────────┘  │  │  (thumbnail of what │  │                      │
│                     │  │   is on screen now) │  │                      │
└─────────────────────┤  └─────────────────────┘  │                      │
                      │                           │                      │
├──────────────────────────────────────────────────────────────────────────┤
│  BOTTOM PANEL — MANUAL SEARCH (height: 240px, bg: bg_panel)              │
│  [🔍 Search scriptures... ] (QLineEdit, full width, 40px height)         │
│  ┌──────────────────────────────────────────────────────────────────┐    │
│  │ Live results list — scrollable, 4 rows visible, max 500 results  │    │
│  │ Format: "John 3:16 — For God so loved the world..."              │    │
│  └──────────────────────────────────────────────────────────────────┘    │
│  [SEND TO DISPLAY ▶]                 [Export Session]                    │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Panel Construction Rules

- Use `QSplitter(Qt.Orientation.Horizontal)` for the three main panels.
  Store splitter handle position in `config.ini [ui] splitter_sizes = 300,400,300`
  and restore on launch.
- Each panel is a `QWidget` with a `QVBoxLayout` and 12px padding.
- Panel headers are `QLabel#label_section` with uppercase letter-spacing.
- The bottom manual search panel is a fixed-height `QWidget` docked at the bottom
  of the window via a `QVBoxLayout` wrapping a `QSplitter` + `QWidget`.
- `QMainWindow.setMinimumSize(1200, 700)`.

---

## PART 3 — AUDIO LEVEL WIDGET (VU METER)

**This is called a "VU Meter" (Volume Unit Meter) or "Audio Level Visualizer".**

File: `ui/audio_meter.py`  
Class: `AudioMeterWidget(QWidget)`

### 3.1 Visual Design

```
┌─────────────────────────────┐
│  ■ ■ ■ ■ ■ ■ ■ ■ ░ ░ ░ ░  │  ← 20 vertical bars
│  ■ ■ ■ ■ ■ ■ ■ ■ ░ ░ ░ ░  │     lit bars = green→amber→red
└─────────────────────────────┘     unlit = dark bg_card
       ↑ bar height reflects RMS amplitude
```

Alternatively, a single horizontal bar with gradient fill is acceptable —
but the 20-bar equalizer style is preferred (more dynamic and visual).

### 3.2 Implementation

```python
class AudioMeterWidget(QWidget):
    """Displays real-time audio input level as animated vertical bars.
    
    Receives RMS float (0.0–1.0) via set_level(). Animates with decay.
    """
    
    BAR_COUNT = 20
    BAR_GAP = 2
    DECAY_RATE = 0.08   # How fast bars fall after peak (per repaint tick)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0         # Current RMS level 0.0–1.0
        self._display_level = 0.0 # Smoothed display level (with decay)
        self._peak = 0.0          # Peak hold value
        self._peak_hold_frames = 0
        
        # 60fps repaint timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60fps
        
        self.setMinimumHeight(48)
        self.setMinimumWidth(120)
    
    def set_level(self, rms: float) -> None:
        """Receive new RMS value from audio thread. Thread-safe via Qt signal."""
        self._level = min(1.0, rms * 3.0)  # Scale up for visibility
    
    def _tick(self) -> None:
        """Called every ~16ms. Applies decay and schedules repaint."""
        if self._level > self._display_level:
            self._display_level = self._level
            self._peak = self._level
            self._peak_hold_frames = 30  # Hold peak for 30 frames (~0.5s)
        else:
            self._display_level = max(0.0, self._display_level - self.DECAY_RATE)
        
        if self._peak_hold_frames > 0:
            self._peak_hold_frames -= 1
        else:
            self._peak = max(0.0, self._peak - self.DECAY_RATE * 0.5)
        
        self._level = 0.0  # Reset; next set_level will raise it again
        self.update()  # Schedule repaint
    
    def paintEvent(self, event) -> None:
        """Draw bars using QPainter."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        bar_width = (w - (self.BAR_COUNT - 1) * self.BAR_GAP) / self.BAR_COUNT
        lit_bars = int(self._display_level * self.BAR_COUNT)
        
        for i in range(self.BAR_COUNT):
            x = int(i * (bar_width + self.BAR_GAP))
            
            if i < lit_bars:
                fraction = i / self.BAR_COUNT
                if fraction < 0.6:
                    color = QColor(COLORS["meter_low"])
                elif fraction < 0.85:
                    color = QColor(COLORS["meter_mid"])
                else:
                    color = QColor(COLORS["meter_high"])
            else:
                color = QColor(COLORS["meter_bg"])
            
            painter.fillRect(int(x), 0, int(bar_width), h, color)
        
        painter.end()
```

### 3.3 Wiring the Meter to Audio

In `core/audio_capture.py`, the sounddevice callback already receives PCM frames.
Add RMS computation and signal emission:

```python
# In AudioCaptureWorker (QObject running in QThread):
audio_level = pyqtSignal(float)   # Emitted every audio callback

def _audio_callback(self, indata, frames, time_info, status):
    """sounddevice callback. Computes RMS and emits level signal."""
    rms = float(np.sqrt(np.mean(indata ** 2)))
    self.audio_level.emit(rms)
    # ... existing chunk accumulation logic
```

In `ui/main_window.py`:
```python
self.audio_worker.audio_level.connect(self.audio_meter.set_level)
```

---

## PART 4 — LIVE TRANSCRIPTION PANEL

File: `ui/transcript_panel.py`  
Class: `TranscriptPanel(QWidget)`

### 4.1 Visual Spec

- `QTextEdit` (read-only, no border) inside a `QWidget#card`.
- Background: `bg_card`. Text: `text_primary`, font `family_mono`, `size_sm`.
- Auto-scrolls to bottom on every new segment append.
- New chunks append with a subtle grey timestamp prefix: `[00:01:23]`.
- When a word or phrase is matched to a detected verse, highlight it in `warning`
  amber color inline within the text (use `QTextCharFormat`).
- A thin animated "pulse" dot (●) at the bottom-left indicates transcription is active.

### 4.2 Implementation

```python
class TranscriptPanel(QWidget):
    """Displays rolling live transcript with inline verse highlights."""
    
    def append_segment(self, text: str, timestamp: float) -> None:
        """Appends a new transcription segment. Auto-scrolls."""
        mins = int(timestamp // 60)
        secs = int(timestamp % 60)
        ts = f"[{mins:02d}:{secs:02d}]"
        
        cursor = self._text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        # Timestamp in muted color
        fmt_ts = QTextCharFormat()
        fmt_ts.setForeground(QColor(COLORS["text_muted"]))
        cursor.setCharFormat(fmt_ts)
        cursor.insertText(f" {ts} ")
        
        # Segment text in primary color
        fmt_text = QTextCharFormat()
        fmt_text.setForeground(QColor(COLORS["text_primary"]))
        cursor.setCharFormat(fmt_text)
        cursor.insertText(text + "\n")
        
        # Always scroll to bottom
        self._text_edit.verticalScrollBar().setValue(
            self._text_edit.verticalScrollBar().maximum()
        )
    
    def highlight_match(self, phrase: str) -> None:
        """Highlights the most recently matched phrase in amber."""
        # Search backward from end, highlight last occurrence of phrase
        document = self._text_edit.document()
        cursor = document.find(
            phrase,
            self._text_edit.textCursor().position() - len(phrase) * 4,
            QTextDocument.FindFlag.FindBackward
        )
        if not cursor.isNull():
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(COLORS["warning"] + "40"))  # 25% opacity
            fmt.setForeground(QColor(COLORS["warning"]))
            cursor.setCharFormat(fmt)
```

---

## PART 5 — SCRIPTURE DETECTION ENGINE (NON-NEGOTIABLE CORE)

### 5.1 Architecture Overview

Two-tier detection runs in a dedicated `DetectionWorker(QObject)` in a `QThread`.
**Never run detection on the UI thread.**

**Tier 1 — Reference Detector (< 2ms):**
Regex patterns that catch explicit spoken references.
Handles: digits AND word-numbers. Examples:
- "John three sixteen" → John 3:16
- "Romans chapter 8 verse 28" → Romans 8:28
- "First Corinthians thirteen four" → 1 Corinthians 13:4
- "Psalm 23" → Psalms 23 (finds whole chapter/first verse)

**Tier 2 — Semantic Similarity (< 50ms per chunk):**
Uses `sentence-transformers` model `all-MiniLM-L6-v2` (22MB, fast CPU inference).
Compares Whisper output against pre-embedded Bible verse corpus.
Threshold: configurable, default **0.50** (50%).
This catches paraphrases, hints, half-remembered quotes.

### 5.2 Startup Embedding (Pre-computation)

On app start, in a `QThread` BEFORE the user clicks Start:

```python
class EmbeddingLoader(QObject):
    """Pre-computes all verse embeddings at startup. Runs once."""
    progress = pyqtSignal(int)       # 0–100 progress bar value
    ready = pyqtSignal(object, object)  # (model, embeddings_matrix)
    
    def run(self) -> None:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        
        # Load model from local cache
        model = SentenceTransformer(
            'all-MiniLM-L6-v2',
            cache_folder=config["transcription"]["model_cache_path"]
        )
        
        # Load all verses from DB
        with BibleDB(config["database"]["db_path"]) as db:
            all_verses = db.get_all_verses()  # Returns list of (ref, text) tuples
        
        texts = [v[1] for v in all_verses]
        refs = [v[0] for v in all_verses]
        
        # Batch encode — emit progress every 1000 verses
        batch_size = 1000
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            emb = model.encode(batch, convert_to_numpy=True, normalize_embeddings=True)
            all_embeddings.append(emb)
            self.progress.emit(int((i / len(texts)) * 100))
        
        matrix = np.vstack(all_embeddings)  # shape: (31102, 384)
        self.ready.emit(model, matrix, refs)
```

**Cache the embeddings** to disk as `data/verse_embeddings.npy` + `data/verse_refs.pkl`.
On subsequent starts, load from cache (< 0.5 seconds) instead of re-encoding.
Invalidate cache only if `KJVBible_Database.db` modification time changes.

### 5.3 Detection Worker

```python
class DetectionWorker(QObject):
    """Runs on a QThread. Receives transcript chunks, emits detected verses."""
    
    verse_detected = pyqtSignal(dict)  
    # Emits: {
    #   "verse_text": str,
    #   "reference": str,
    #   "confidence": float,      # 0.0–1.0
    #   "method": str,            # "reference" | "semantic"
    #   "matched_phrase": str,    # The phrase in transcript that triggered this
    # }
    
    def __init__(self, model, embeddings, refs, config):
        super().__init__()
        self._model = model
        self._embeddings = embeddings  # numpy (N, 384) float32, L2-normalized
        self._refs = refs              # list of "Book Chapter:Verse" strings
        self._config = config
        self._threshold = float(config["detection"]["confidence_threshold"])
        self._detector = VerseDetector()  # Tier 1 regex
        
        # Sliding window buffer: last 15 seconds of transcript
        self._buffer = []        # list of (timestamp, text) tuples
        self._buffer_window = 15 # seconds
    
    @pyqtSlot(str, float)
    def process_chunk(self, text: str, timestamp: float) -> None:
        """Called for each Whisper chunk. Runs both detection tiers."""
        # 1. Maintain sliding window buffer
        self._buffer.append((timestamp, text))
        cutoff = timestamp - self._buffer_window
        self._buffer = [(t, x) for t, x in self._buffer if t >= cutoff]
        window_text = " ".join(x for _, x in self._buffer)
        
        # 2. Tier 1 — Reference Detection (fast regex)
        matches = self._detector.detect(window_text)
        for match in matches:
            if match["confidence"] >= self._threshold:
                verse = lookup_verse(match["reference"])
                if verse:
                    self.verse_detected.emit({**match, "verse_text": verse})
                    return  # Tier 1 hit — skip Tier 2 for this chunk
        
        # 3. Tier 2 — Semantic Similarity
        import numpy as np
        query_emb = self._model.encode(
            [window_text[-500:]],  # Last 500 chars for speed
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        # Cosine similarity via dot product (embeddings are L2-normalized)
        scores = np.dot(self._embeddings, query_emb[0])  # shape: (N,)
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])
        
        if best_score >= self._threshold:
            ref = self._refs[best_idx]
            verse_text = lookup_verse_by_index(best_idx)
            self.verse_detected.emit({
                "verse_text": verse_text,
                "reference": ref,
                "confidence": best_score,
                "method": "semantic",
                "matched_phrase": window_text[-100:],
            })
```

### 5.4 Speed Optimizations (mandatory)

1. **Embeddings are float32, L2-normalized** — dot product IS cosine similarity. No extra normalization step.
2. **numpy.dot is BLAS-optimized** — 31,102 × 384 dot product takes ~5ms on CPU.
3. **Only encode the LAST 500 characters** of the sliding window — smaller input = faster encode.
4. **Debounce**: Do not run Tier 2 more than once per 2 seconds on the same text.
   Use a hash of the last 100 chars as a dedup key.
5. **model.encode() with `show_progress_bar=False`** — no stdout noise.
6. **Confidence threshold at 0.50** means ~half the sermons will surface matches.
   Operator always approves/dismisses — false positives are acceptable.

---

## PART 6 — APPROVAL PANEL

File: `ui/approval_panel.py`  
Class: `ApprovalPanel(QWidget)`

### 6.1 Visual Spec

When a verse is detected, this panel "activates" with an amber border glow.
It shows:

```
┌────────────────────────────────────────────────┐  ← amber border (2px) when active
│  ● DETECTED  [semantic | 73%]                  │  ← method + confidence badge
│                                                │
│  "For God so loved the world, that he gave     │  ← verse text (size_lg, white)
│   his only begotten Son, that whosoever         │
│   believeth in him should not perish..."        │
│                                                │
│  John 3:16  ·  KJV                             │  ← reference (accent blue)
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ ✓ SEND   │  │ ✗ SKIP   │  │  ✏ EDIT REF  │  │
│  │ (green)  │  │ (red)    │  │  (muted)     │  │
│  └──────────┘  └──────────┘  └──────────────┘  │
│                                                │
│  [Auto-send in 5s ░░░░░░░░░░░░░░░░░░░░░░░░░] ← progress bar if auto-send on │
└────────────────────────────────────────────────┘
```

When no verse is detected:
```
┌────────────────────────────────────────────────┐  ← muted border (1px)
│        Listening for scripture...              │  ← centered, text_muted
└────────────────────────────────────────────────┘
```

### 6.2 Signals

```python
class ApprovalPanel(QWidget):
    verse_sent = pyqtSignal(dict)     # Operator approved → send to display
    verse_dismissed = pyqtSignal()    # Operator skipped
```

### 6.3 Auto-Send Timer

- Timer only starts if `config["detection"]["auto_send_enabled"] == "true"`
- `QProgressBar` shows countdown visually
- Operator pressing SKIP or SEND cancels the timer immediately
- Timer duration from `config["detection"]["auto_send_delay_seconds"]`

---

## PART 7 — SCRIPTURE DISPLAY WINDOW

File: `ui/scripture_display.py`  
Class: `ScriptureDisplay(QWidget)`

### 7.1 Layout

```
Full black screen (or second monitor)

             [Translation Label — top center, muted small]
                          KJV

     [Verse Body — center, large white text, word-wrapped]
     For God so loved the world, that he gave
     his only begotten Son, that whosoever
     believeth in him should not perish, but
     have everlasting life.

             [Reference — bottom center, accent blue]
                       John 3:16
```

### 7.2 Fade Animation

```python
def show_verse(self, text: str, reference: str, translation: str = "KJV") -> None:
    """Fades in new verse. Replaces current if any."""
    # 1. Set new content
    self._verse_label.setText(text)
    self._ref_label.setText(reference)
    self._trans_label.setText(translation)
    
    # 2. Fade in using QPropertyAnimation on windowOpacity
    self._fade_in()

def _fade_in(self) -> None:
    self._anim = QPropertyAnimation(self, b"windowOpacity")
    self._anim.setDuration(int(self._config["display"]["fade_in_ms"]))
    self._anim.setStartValue(0.0)
    self._anim.setEndValue(1.0)
    self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    self.show()
    self._anim.start()

def clear_display(self) -> None:
    """Fades out and clears."""
    self._anim = QPropertyAnimation(self, b"windowOpacity")
    self._anim.setDuration(int(self._config["display"]["fade_out_ms"]))
    self._anim.setStartValue(1.0)
    self._anim.setEndValue(0.0)
    self._anim.finished.connect(self.hide)
    self._anim.start()
```

### 7.3 Monitor Placement

```python
def move_to_monitor(self, index: int) -> None:
    """Moves window to target monitor. Falls back to primary if index invalid."""
    screens = QApplication.screens()
    target = screens[index] if index < len(screens) else screens[0]
    geo = target.geometry()
    self.setGeometry(geo)
    self.showFullScreen()
```

---

## PART 8 — LIVE SEARCH PANEL

### 8.1 SQLite FTS5 Setup

In `core/bible_db.py`, add a one-time setup method:

```python
def build_fts_index(self) -> None:
    """Creates FTS5 virtual table for fast full-text search. Idempotent."""
    with self._connect() as conn:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS bible_fts
            USING fts5(reference UNINDEXED, verse, content=bible, content_rowid=rowid)
        """)
        conn.execute("INSERT INTO bible_fts(bible_fts) VALUES('rebuild')")
        conn.commit()

def search_fts(self, query: str, limit: int = 200) -> list[dict]:
    """Full-text search. Returns list of {reference, verse, snippet} dicts."""
    if not query.strip():
        return []
    clean = query.strip().replace('"', '').replace("'", "")
    fts_query = " OR ".join(f'"{word}"' for word in clean.split()[:5])
    with self._connect() as conn:
        cursor = conn.execute(f"""
            SELECT b.Book, b.Chapter, b.VerseNumber, b.Verse,
                   highlight(bible_fts, 1, '<MATCH>', '</MATCH>') as snippet
            FROM bible_fts
            JOIN bible b ON bible_fts.rowid = b.rowid
            WHERE bible_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (fts_query, limit))
        rows = cursor.fetchall()
    return [{"reference": build_ref(r[0], r[1], r[2]), "verse": r[3], "snippet": r[4]}
            for r in rows]
```

Also add a simple `LIKE`-based fallback for short queries (1–2 chars):
```python
def search_like(self, query: str, limit: int = 200) -> list[dict]:
    """LIKE-based search for short queries where FTS is less effective."""
    with self._connect() as conn:
        cursor = conn.execute("""
            SELECT Book, Chapter, VerseNumber, Verse FROM bible
            WHERE LOWER(Verse) LIKE LOWER(?)
            LIMIT ?
        """, (f"%{query}%", limit))
        ...
```

### 8.2 Search Widget

File: `ui/manual_lookup.py`  
Class: `ManualLookup(QWidget)`

```python
class ManualLookup(QWidget):
    send_to_display = pyqtSignal(dict)  # {verse_text, reference, translation}
    
    def __init__(self, bible_db, parent=None):
        super().__init__(parent)
        self._db = bible_db
        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.timeout.connect(self._run_search)
        self._results = []
        self._setup_ui()
    
    def _on_text_changed(self, text: str) -> None:
        """Fires on every keystroke. Debounced 120ms for smooth typing."""
        self._debounce.start(120)
    
    def _run_search(self) -> None:
        query = self._search_input.text().strip()
        if len(query) < 2:
            self._results_list.clear()
            return
        
        if len(query) <= 3:
            results = self._db.search_like(query, limit=100)
        else:
            results = self._db.search_fts(query, limit=200)
        
        self._results = results
        self._populate_list(results)
    
    def _populate_list(self, results: list) -> None:
        """Repopulates the QListWidget with results."""
        self._results_list.clear()
        for r in results:
            item = QListWidgetItem(f"{r['reference']}  —  {r['verse'][:80]}...")
            item.setData(Qt.ItemDataRole.UserRole, r)
            self._results_list.addItem(item)
    
    def _on_item_double_clicked(self, item) -> None:
        """Double-click or Enter sends verse to display."""
        data = item.data(Qt.ItemDataRole.UserRole)
        self.send_to_display.emit({
            "verse_text": data["verse"],
            "reference": data["reference"],
            "translation": "KJV",
        })
```

**Search input styling:** 40px height, large search icon on left (🔍 via QPainter or emoji label), placeholder text "Search by keyword or reference — e.g. 'John 3:16' or 'love'".

**Results list:** `QListWidget`, max visible height `160px` (scrollable), items 36px tall with reference in bold accent color and verse preview in text_secondary color. Use a custom `QStyledItemDelegate` for two-line rendering.

---

## PART 9 — REQUIREMENTS.TXT ADDITIONS

Add these packages (check they're not already present):

```
sentence-transformers>=2.7.0
torch>=2.2.0          # CPU-only is fine: torch==2.2.0+cpu via --extra-index-url
numpy>=1.26.0
```

**Windows CPU-only torch install** (add to README setup instructions):
```
pip install torch==2.2.0+cpu --extra-index-url https://download.pytorch.org/whl/cpu
pip install sentence-transformers
```

The `all-MiniLM-L6-v2` model (22MB) will download to the HuggingFace cache on first
semantic detection run. It is much smaller than Whisper and downloads in seconds.

---

## PART 10 — SETTINGS DIALOG

File: `ui/settings_dialog.py`  
Sections (use a `QTabWidget` with tabs):

**Tab 1 — Audio**
- Input device selector (QComboBox, populated with sounddevice.query_devices())
- Sample rate (16000 fixed, informational label only)
- Test audio button → opens brief mic level modal

**Tab 2 — Detection**
- Confidence threshold: QSlider (0–100%) + live label showing current %
- Auto-send toggle: QCheckBox
- Auto-send delay: QSpinBox (1–30 seconds)
- Detection method: checkboxes for [✓ Reference Regex] [✓ Semantic AI]

**Tab 3 — Display**
- Monitor selector: QComboBox (populated from QApplication.screens())
- Font size for verse body: QSpinBox
- Background color picker: QPushButton that opens QColorDialog
- Test display button: sends a sample verse to the display window

**Tab 4 — Session**
- Session log folder: QLineEdit + Browse button
- Export format: radio buttons (TXT / JSON)

---

## PART 11 — TASK TABLE (Ordered Build Sequence)

Execute these in exact order. No skipping. No bundling.

| ID | Task | File | Agent | Notes |
|----|------|------|-------|-------|
| R-01 | Read all three config files | — | @build | Mandatory loop entry |
| R-02 | Audit existing file structure against file_structure.txt | — | @architect | Note any missing or broken files |
| R-03 | Write complete `ui/styles.py` | ui/styles.py | @build | COLORS, FONTS, RADIUS, SPACING, get_stylesheet() |
| R-04 | Write `ui/audio_meter.py` — AudioMeterWidget | ui/audio_meter.py | @architect | Full implementation per Part 3 |
| R-05 | Update `core/audio_capture.py` — add RMS signal | core/audio_capture.py | @architect | Per Part 3.3 |
| R-06 | Update `core/bible_db.py` — add FTS5 + search methods | core/bible_db.py | @build | Per Part 8.1 |
| R-07 | Write embedding cache system in `core/embedding_cache.py` | core/embedding_cache.py | @architect | Pre-compute + cache embeddings per Part 5.2 |
| R-08 | Update `core/verse_detector.py` — add semantic tier | core/verse_detector.py | @architect | Per Part 5.3, DetectionWorker class |
| R-09 | Rewrite `ui/transcript_panel.py` | ui/transcript_panel.py | @build | Per Part 4 |
| R-10 | Rewrite `ui/approval_panel.py` | ui/approval_panel.py | @architect | Per Part 6 |
| R-11 | Rewrite `ui/scripture_display.py` | ui/scripture_display.py | @architect | Per Part 7 |
| R-12 | Rewrite `ui/manual_lookup.py` | ui/manual_lookup.py | @architect | Per Part 8.2 |
| R-13 | Rewrite `ui/history_panel.py` | ui/history_panel.py | @build | Styled to design system |
| R-14 | Rewrite `ui/settings_dialog.py` | ui/settings_dialog.py | @build | Per Part 10 |
| R-15 | Rewrite `ui/main_window.py` | ui/main_window.py | @architect | Full layout per Part 2; wires all components |
| R-16 | Update `main.py` — startup embedding load, splash, launch | main.py | @architect | EmbeddingLoader in QThread; progress shown on launch |
| R-17 | Update `config/config.ini` — add all new keys | config/config.ini | @build | Per project_config.md Section 7 |
| R-18 | Update `requirements.txt` | requirements.txt | @build | Add sentence-transformers, torch CPU |
| R-19 | Smoke test: launch app, verify UI renders | — | @architect | All panels visible, no import errors |
| R-20 | Test audio meter: select mic, speak, verify bar animation | — | @architect | Bars must respond within 100ms |
| R-21 | Test transcription: speak clearly, verify text appears live | — | @architect | Text must appear within 6 seconds of speech |
| R-22 | Test Tier 1 detection: say "John 3 16", verify detection | — | @architect | Must detect with confidence > 0.85 |
| R-23 | Test Tier 2 detection: say paraphrase, verify detection | — | @architect | e.g. "God loved the world so much he sent his son" |
| R-24 | Test live search: type "love", verify results appear | — | @build | Must show results within 150ms of each keystroke |
| R-25 | Test display window: approve verse, verify fullscreen render | — | @build | Fade in must be smooth |
| R-26 | Run full pytest suite — all existing tests must still pass | — | @architect | Fix any regressions from rewrites |
| R-27 | Phase commit: `feat(rebuild): UI redesign and core pipeline` | — | @build | Push to origin main |

---

## PART 12 — CRITICAL IMPLEMENTATION RULES

1. **Never block the main UI thread.** Transcription, embedding encoding, and detection all run in `QThread`s. Communication is via PyQt signals only.

2. **Audio meter must feel real-time.** The decay rate and repaint timer determine how "alive" it feels. Use 60fps repaint, smooth decay, peak hold. Test by whistling — the bars should follow your voice immediately.

3. **Semantic detection must not stutter the UI.** If `model.encode()` takes 40ms, that is acceptable in a background thread. If it causes the transcript to lag, reduce batch size or add a queue.

4. **Live search must feel instant.** 120ms debounce + SQLite FTS5 means results should appear while the user is still typing. If results take > 200ms, add an explicit async query pattern.

5. **Every file must use COLORS from `ui/styles.py`.** No hardcoded hex values anywhere. No inline `setStyleSheet("color: #fff")` calls — all styling goes through the master QSS.

6. **The display window must be movable to Monitor 2.** Test with a single monitor by validating fallback logic. Never let the window end up off-screen.

7. **The confidence threshold default is 0.50**, not 0.75. Update `config/config.ini` to reflect this.

---

## PART 13 — WHAT "DONE" LOOKS LIKE

The rebuild is complete when ALL of the following are true simultaneously:

- [ ] App launches without errors. Startup embedding load shows a progress bar.
- [ ] Audio device dropdown lists real devices. Selecting one starts the meter.
- [ ] Audio meter bars animate visibly when speaking, decay when silent.
- [ ] Clicking START begins live transcription. Text appears in the left panel within 6 seconds.
- [ ] Speaking a verse reference ("John 3:16") surfaces a detection card within 8 seconds.
- [ ] Speaking a paraphrase with 50%+ semantic match surfaces a detection card.
- [ ] Typing in the search bar shows results after each keystroke (debounced).
- [ ] Pressing SEND on the approval panel shows the verse fullscreen in the display window.
- [ ] All text, backgrounds, and accents match the COLORS token system.
- [ ] No UI element is hardcoded outside of `ui/styles.py`.
- [ ] All pytest tests pass.

---

---

## PART 14 — FULL TEST SUITE

### 14.1 Unit Tests

**File: `tests/test_audio_meter.py`**
- Instantiate `AudioMeterWidget` headlessly (pytest-qt)
- `set_level(0.0)` → `_display_level` stays 0
- `set_level(1.0)` → `_display_level` reaches 1.0 after one tick
- `set_level(0.8)` then no more calls → `_display_level` decays to 0 over N ticks
- `_peak` holds for `PEAK_HOLD_FRAMES` then decays
- `paintEvent` does not crash on zero-size widget
- `set_level` called from non-main thread does not crash (thread safety check)

**File: `tests/test_embedding_cache.py`**
- Cache file does not exist → `EmbeddingLoader.run()` builds and saves `.npy` + `.pkl`
- Cache file exists → loads from disk, skips encoding (mock `model.encode` to assert not called)
- DB modification time newer than cache → cache is rebuilt
- `progress` signal emits values 0 → 100 in order
- `ready` signal emits matrix shape `(31102, 384)` and refs list length `31102`
- Embeddings are float32 and L2-normalized: `np.linalg.norm(row) ≈ 1.0` for every row

**File: `tests/test_detection_worker.py`**
- **Tier 1 — explicit references:**
  - "John three sixteen" → `{reference: "John 3:16", method: "reference", confidence: >= 0.85}`
  - "Romans chapter eight verse twenty-eight" → `Romans 8:28`
  - "First Corinthians thirteen four" → `1 Corinthians 13:4`
  - "Psalm twenty-three" → `Psalms 23:1`
  - "Revelation chapter twenty-two verse twenty-one" → `Revelation 22:21`
  - Gibberish text → no detection emitted
  - Empty string → no detection emitted
- **Tier 2 — semantic:**
  - "God loved the world so much he sent his only son" → match near John 3:16, confidence >= 0.50
  - "The Lord is my shepherd, I shall not want" → match near Psalms 23:1, confidence >= 0.60
  - "I can do all things through Christ" → match near Philippians 4:13, confidence >= 0.55
  - Random noise sentence ("the cat sat on the mat") → confidence < 0.50, no emission
- **Threshold filter:**
  - Set threshold to 0.99 → no semantic matches emitted for any sermon sentence
  - Set threshold to 0.01 → semantic match emitted for every chunk
- **Dedup:**
  - Same chunk text sent twice within 2 seconds → `verse_detected` emitted only once
  - Same text after 3 seconds → emitted again (dedup expired)
- **Sliding window:**
  - Buffer correctly drops segments older than 15 seconds

**File: `tests/test_bible_db_fts.py`** (extends existing test_bible_db.py)
- `build_fts_index()` is idempotent (call twice, no error, same row count)
- `search_fts("love")` returns list, each item has keys: `reference`, `verse`, `snippet`
- `search_fts("John 3:16")` → first result reference is "John 3:16"
- `search_fts("rejoice")` → returns at least 10 results
- `search_fts("")` → returns empty list (no crash)
- `search_fts("xyznotaword")` → returns empty list
- `search_like("God so loved")` → at least 1 result containing John 3:16
- Result count never exceeds `limit` parameter
- All results are dicts — no raw tuples leaking

**File: `tests/test_transcript_panel.py`**
- `append_segment("Hello world", 5.0)` → text widget contains "[00:05] Hello world"
- `append_segment` called 100 times → auto-scroll position is at maximum
- `highlight_match("Hello")` → that word has amber background in document
- Panel renders in headless Qt without crash

**File: `tests/test_approval_panel.py`**
- No detection → panel shows "Listening for scripture..." placeholder
- `show_detection(verse_data)` → panel shows verse text, reference, confidence badge
- Click SEND → `verse_sent` signal emitted with correct dict
- Click SKIP → `verse_dismissed` signal emitted, panel resets to placeholder
- EDIT mode: reference text becomes editable QLineEdit; confirm emits modified reference
- Auto-send enabled, delay=1s → `verse_sent` emits after 1s without operator action
- Auto-send: clicking SKIP within 1s cancels timer, no emission
- Confidence badge color: >= 0.75 green, 0.50–0.74 amber, < 0.50 red

**File: `tests/test_manual_lookup.py`**
- Typing "love" → results list populated within 200ms (QTest.qWait)
- Typing "" or single char → results list is empty
- Typing "John 3:16" → first result reference matches "John 3:16"
- Double-clicking result → `send_to_display` signal emitted with correct verse dict
- Results never exceed 200 items
- Typing fast (simulate 10 keystrokes, 50ms apart) → only one DB query fires per debounce period (mock DB, assert call count)

**File: `tests/test_scripture_display.py`** (extend existing)
- `show_verse(text, ref, trans)` → all three labels populated
- `clear_display()` called while showing → widget hides after fade duration
- `move_to_monitor(0)` on single-monitor machine → window on primary screen, no crash
- `move_to_monitor(99)` → falls back to primary screen (no crash, no off-screen window)
- `show_verse` called while already showing → previous content replaced, animation restarts

### 14.2 Integration Tests

**File: `tests/test_integration_pipeline.py`**

These tests wire real components together without mocks.

```python
# Test I-01: Audio → Transcript
# Feed a pre-recorded WAV file of "John 3:16" spoken aloud
# through AudioCaptureWorker → TranscriberWorker
# Assert: TranscriptPanel receives at least one segment containing "John"
# within 10 seconds (QTest.qWait(10000))

# Test I-02: Transcript → Detection (Tier 1)
# Feed transcript text "Romans eight twenty eight" directly to DetectionWorker
# Assert: verse_detected signal emits within 3 seconds
# Assert: reference == "Romans 8:28"
# Assert: method == "reference"

# Test I-03: Transcript → Detection (Tier 2)  
# Feed transcript text "the Lord is my shepherd" to DetectionWorker
# Assert: verse_detected emitted, confidence >= 0.50
# Assert: reference contains "Psalm" or "Psalms"

# Test I-04: Detection → Approval → Display
# Inject a verse_detected dict into ApprovalPanel
# Simulate SEND button click
# Assert: ScriptureDisplay.isVisible() == True
# Assert: verse label text matches verse_text from dict

# Test I-05: Search → Display
# Type "everlasting life" into ManualLookup search field (QTest.keyClicks)
# Wait 200ms for debounce
# Assert: results list is not empty
# Double-click first result
# Assert: send_to_display signal emitted
```

### 14.3 Performance Tests

**File: `tests/test_performance.py`**

```python
# Perf-01: Semantic similarity speed
# Run DetectionWorker.process_chunk() with a 500-char text
# Assert: completes in < 100ms (time.perf_counter)
# Run 10 consecutive chunks, assert mean < 80ms

# Perf-02: FTS5 search speed
# Call search_fts("love") 20 times
# Assert: every call completes in < 50ms

# Perf-03: LIKE search speed
# Call search_like("God") 20 times
# Assert: every call < 100ms

# Perf-04: Embedding cache load speed
# With cache file present, time EmbeddingLoader.load_from_cache()
# Assert: < 1000ms (1 second)

# Perf-05: Audio meter repaint speed
# Call AudioMeterWidget.update() 60 times (simulating 1 second at 60fps)
# Assert: total repaint time < 200ms
```

### 14.4 Edge Case & Robustness Tests

**File: `tests/test_edge_cases.py`**

- Verse detector with ALL CAPS input: "JOHN THREE SIXTEEN" → detects correctly
- Verse detector with heavy background noise transcript (random words) → no false emission for 10 consecutive chunks of pure noise
- DB lookup for non-existent verse (Book=99, Chapter=1, Verse=1) → returns None, no exception
- DB lookup for Book=1, Chapter=1, Verse=1 (Genesis 1:1) → returns correct text
- Transcript panel: appending 10,000 segments → no memory crash, scroll still works
- Audio meter: `set_level` called 1000 times per second → no queue overflow, UI stays responsive
- Settings dialog: set monitor_index to 99 → saved to config, display window falls back gracefully on next launch
- App launch with no audio devices connected → clear error message shown in header, app does not crash
- App launch with corrupted/missing KJVBible_Database.db → shows error dialog with file path, does not crash silently

### 14.5 Test Execution Order

Run in this order. Each group must pass before the next starts.

### 14.6 Test Infrastructure Requirements

Add to `tests/conftest.py`:
```python
import pytest
from pytestqt.plugin import QtBot
from configparser import ConfigParser

@pytest.fixture(scope="session")
def app_config():
    """Loads real config.ini for all tests."""
    config = ConfigParser()
    config.read("config/config.ini")
    return config

@pytest.fixture(scope="session")
def bible_db(app_config):
    """Real BibleDB instance, shared across session."""
    from core.bible_db import BibleDB
    db = BibleDB(app_config["database"]["db_path"])
    db.build_fts_index()
    return db

@pytest.fixture(scope="session")
def embedding_data(app_config):
    """Pre-loaded embeddings for detection tests (slow, load once)."""
    from core.embedding_cache import load_or_build
    return load_or_build(app_config)
```

---

*End of PLAN.md*
