# BUGS AND ACTION PLAN

## 1. IDENTIFIED BUGS & ISSUES

### 1.1 Critical / Runtime Errors
| ID | Issue | Location | Impact |
|---|---|---|---|
| B-01 | `KeyError: 'error'` | `ui/main_window.py:146` | **CRITICAL**: Application crashes immediately when clicking "START". |
| B-02 | Book Name -> ID Mismatch | `core/verse_detector.py` / `core/bible_db.py` | **CRITICAL**: Tier 1 detection fails to fetch verse text because it passes a string ("John") to a function expecting an integer (43). |
| B-03 | Missing Tier 2 Wiring | `ui/main_window.py` | **HIGH**: Semantic detection (Tier 2) is never actually activated because models are not passed to the worker. |
| B-04 | Config Path Resolution | `core/bible_db.py` | **HIGH**: BibleDB looks for `config.ini` in root, but it resides in `config/`. Falls back to default paths which may be incorrect. |

### 1.2 Performance Issues
| ID | Issue | Location | Impact |
|---|---|---|---|
| P-01 | FTS Index Rebuild | `core/bible_db.py` | **SEVERE**: The FTS5 index is dropped and rebuilt on EVERY `BibleDB` instantiation. This adds massive latency to every search and detection. |
| P-02 | Whisper Engine Choice | `core/transcriber.py` | **MEDIUM**: Uses `openai-whisper` instead of `faster-whisper`. May be too slow for real-time 5s chunks on mid-range CPUs. |

### 1.3 Consistency & Spec Deviations
| ID | Issue | Location | Impact |
|---|---|---|---|
| S-01 | Model Size Mismatch | `config/config.ini` | Specified `medium.en` in docs, but `base.en` is configured. `base.en` is less accurate for sermons. |
| S-02 | Reference Display | `core/bible_db.py` | Displays book IDs (e.g., "43 3:16") instead of names ("John 3:16"). |
| S-03 | Missing Test Dependencies | `requirements.txt` | `pytest-timeout` is missing, causing test failures if run with specified flags. |

---

## 2. DETAILED RESOLUTION PLAN

### Step 1: Fix B-01 (KeyError)
- Change `COLORS['error']` to `COLORS['danger']` in `ui/main_window.py`.

### Step 2: Fix B-04 (Config Path)
- Update `core/bible_db.py` to correctly locate `config/config.ini`.

### Step 3: Fix P-01 (FTS Rebuild)
- Modify `BibleDB._build_fts_index` to only rebuild if the table doesn't exist or if explicitly requested.

### Step 4: Fix B-02 & S-02 (Book Mapping)
- Create a Name -> ID mapping (e.g., in `data/book_names.py` or `core/bible_db.py`).
- Update `DetectionWorker` to use ID for DB lookups.
- Update `build_ref` to use Name for display.

### Step 5: Fix B-03 (Tier 2 Wiring)
- Update `MainWindow.on_models_ready` to pass the model, matrix, and refs to the `DetectionWorker`.

### Step 6: Environment Cleanup
- Install `pytest-timeout`.
- Update `requirements.txt`.

### Step 7: Verification
- Run the fixed app.
- Run tests (fixing any that were broken by these changes).
