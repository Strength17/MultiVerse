# Building MultiVerse (Windows desktop)

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
pyinstaller multiverse.spec --noconfirm
```

Output: `dist/MultiVerse/MultiVerse.exe`

## Build installer

```powershell
iscc installer\MultiVerse.iss
```

Output: `installer/output/MultiVerse-Setup-1.1.0.exe`

## Run without packaging

```powershell
python desktop_app.py
```

Or legacy browser mode: `Start MultiVerse.bat` (opens UI at http://127.0.0.1:8766/ui/index.html once server is up).

## User data locations (installed app)

| What | Where |
|------|--------|
| Bible databases | `Documents\MultiVerse\data\<Version>\<Language>\*.sqlite3` |
| Vector index | `Documents\MultiVerse\data\bible_vectors.index` |
| Verse map | `Documents\MultiVerse\data\bible_verse_map.pkl` |
| Background images | `Documents\MultiVerse\data\backgrounds\` |
| Display settings | `Documents\MultiVerse\config\display_user.json` |
| Session transcripts | `Documents\MultiVerse\Transcription\` |
| Logs | `Documents\MultiVerse\logs\` |

## NDI test

In the app: **Recall → vMix** tab → **Send test verse to NDI**. Add **NDI → MultiVerse** in vMix.
