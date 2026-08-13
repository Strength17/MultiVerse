# MultiVerse

Live Bible verse display for church services. Speak a reference or paraphrase a passage — MultiVerse detects it, shows it on screen, and can send it to vMix over NDI.

**Version:** 0.0.1.0

---

## Download

**[Download MultiVerse 0.0.1.0 (ZIP)](https://github.com/Strength17/WindowVerse/releases/download/0.0.1.0/MultiVerse-0.0.1.0.zip)**

The ZIP contains:

- `MultiVerse-Setup-0.0.1.0.exe` — installer
- `setup.txt` — full checklist (read this first)

---

## Before you install (required)

### The one test that must pass

MultiVerse uses **Windows voice typing**. If this fails, the app cannot work.

1. Open **Notepad**
2. Press **Win + H**
3. Speak in **English**
4. English text must appear as you talk

Fix Windows speech settings before installing MultiVerse. See `setup.txt` in the download for details.

### Quick checklist

- [ ] **Windows 11** (64-bit)
- [ ] **Microphone** connected and working
- [ ] **Win + H** test passed (above)
- [ ] **English (United States)** installed — Settings → Time & language
- [ ] **Microphone access** allowed for desktop apps — Settings → Privacy → Microphone

---

## Install

1. Download and unzip **MultiVerse-0.0.1.0.zip**
2. Read **setup.txt**
3. Run **MultiVerse-Setup-0.0.1.0.exe**
4. Launch **MultiVerse** from the Start menu

---

## Add your Bible database

The installer does **not** include Bible text files. Copy your database after install:

```
Documents\MultiVerse\data\NKJV\English\NKJV.sqlite3
```

Example layout:

```
Documents\MultiVerse\data\
  NKJV\
    English\NKJV.sqlite3
    French\FreBBB.db          (optional — for on-screen French text)
  backgrounds\                (optional — custom background images)
```

Restart MultiVerse after adding files. New versions in that folder are picked up automatically.

---

## First use

1. Open MultiVerse and wait until **Start** is enabled (loading bar finishes).
2. Click **Start** to open the microphone.
3. Say a reference: *"Genesis chapter 1 verse 1"*
4. The verse appears in **Live Output** (and on NDI if enabled).

### Search bar

On the **Live** page, use the bottom **Search** box for phrases or references, e.g.:

- *"the lord is my shepherd"*
- *"John 3:16"*

Results are grouped **Old Testament** / **New Testament**. Click a result to put it on screen.

### Settings

Open the sidebar → **Settings** for:

- Bible version
- Microphone device
- Story narration sensitivity
- Search scope (All / OT / NT)
- Auto-save transcript delay after silence
- Verse appearance (colors, font, NDI layout)

Transcripts save to:

```
Documents\MultiVerse\Transcription\
```

---

## Optional: vMix / NDI

1. Install [NDI Tools](https://ndi.video/tools/) on the MultiVerse PC.
2. In vMix: **Add Input → NDI → MultiVerse**
3. In MultiVerse: **Recall → vMix** tab → send a test verse to confirm.

See **NDI_SETUP.md** in the install folder for troubleshooting.

---

## Important notes

| Topic | Detail |
|--------|--------|
| **Speech language** | English only for live transcription (Windows dictation) |
| **French on screen** | Supported if you add a French Bible database; speech is still English |
| **Offline use** | Verse detection works offline after the first-time model cache is built |
| **Logs** | `Documents\MultiVerse\logs\` — errors never appear in the transcript |

---

## For developers

Clone this repo and run from source:

```powershell
pip install -r requirements_winrt.txt --break-system-packages
python desktop_app.py
```

Build the release package:

```powershell
pyinstaller multiverse.spec --noconfirm
iscc installer\MultiVerse.iss
powershell -File scripts\package_release.ps1
```

Run tests:

```powershell
python scripts/smoke_preflight.py
```

More detail: **BUILD.md**, **COMMANDS.md**, **NDI_SETUP.md**.

---

## License

See repository license. Bible database files are your responsibility to supply and must comply with their publishers' terms.
