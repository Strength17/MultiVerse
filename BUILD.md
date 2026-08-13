# Building Window Verse (Windows desktop)

## Prerequisites

1. Python 3.11+ with dependencies: `pip install -r requirements_winrt.txt --break-system-packages`
2. Build tools: `pip install -r build/requirements-build.txt --break-system-packages`
3. **Inno Setup 6** (for the installer) — https://jrsoftware.org/isinfo.php
4. **NDI Runtime** (optional, on target machine) — for vMix output

## Generate icon

```powershell
python assets/make_icon.py
```

## Build executable

```powershell
pyinstaller windowverse.spec --noconfirm
```

Output: `dist/Window Verse/Window Verse.exe`

## Build installer

```powershell
iscc installer\Window Verse.iss
```

Output: `installer/output/Window Verse-Setup-1.1.0.exe`

## Run without packaging

```powershell
python desktop_app.py
```

Or legacy browser mode: `Start Window Verse.bat` (opens UI at http://127.0.0.1:8766/ui/index.html once server is up).

## Testing before building the installer

Do **not** run PyInstaller or Inno Setup until dev testing passes. Use this order:

### 1. Dev run (primary test mode)

```powershell
cd "c:\Users\Strength Awa\Desktop\BUSINESS\Multiverse"
.\.venv\Scripts\Activate.ps1
python desktop_app.py
```

Restart the app after UI or Python changes. This matches the shipped WebView2 experience.

Browser-only UI iteration:

```powershell
python server.py
# open http://127.0.0.1:8766/ui/index.html
```

### 2. Automated smoke checks (no microphone)

```powershell
python scripts/test_verse_detection.py
python inspect_bible_db.py data\NKJV\French\FreBBB.db --sample
```

### 3. Manual checklist

- [ ] Startup bar shows loading steps and progress before **Start** enables
- [ ] **Start** → mic ring, progress bar, and status pill appear immediately
- [ ] Speak a verse reference → transcript + suggestion card appear
- [ ] Bottom dock: **Explicit** / **Paraphrase** / **All** search tabs work
- [ ] Recent Verses populate and are clickable (re-send to stage)
- [ ] Resize window: layout adapts at 1200 / 900 / 600 px widths
- [ ] Settings accessible via sidebar (Bible, Microphone, Appearance)
- [ ] Logs tab shows mic errors (not in transcript)
- [ ] Header has no engine/STT technology badge

### 4. Frozen bundle test (still not the installer)

Only after the checklist passes:

```powershell
pyinstaller windowverse.spec --noconfirm
.\dist\Window Verse\Window Verse.exe
```

Place test Bible DBs under `Documents\Window Verse\data\` and re-run the checklist.

### 5. Installer (explicit approval only)

```powershell
iscc installer\Window Verse.iss
```

Output: `installer/output/Window Verse-Setup-1.1.0.exe`

## User data locations (installed app)

| What | Where |
|------|--------|
| Bible databases | `Documents\Window Verse\data\<Version>\<Language>\*.sqlite3` |
| Vector index | `Documents\Window Verse\data\bible_vectors.index` |
| Verse map | `Documents\Window Verse\data\bible_verse_map.pkl` |
| Background images | `Documents\Window Verse\data\backgrounds\` |
| Display settings | `Documents\Window Verse\config\display_user.json` |
| Session transcripts | `Documents\Window Verse\Transcription\` |
| Logs | `Documents\Window Verse\logs\` |

## NDI test

In the app: **Recall → vMix** tab → **Send test verse to NDI**. Add **NDI → Window Verse** in vMix.
