# Implementation Plan - Layout Alignment, Resizing Handles, Vertical Position, Font Color & Error Quiet

This plan covers resolving the browser-side settings visibility bug, fixing the voice commands, implementing vertical text alignment, matching the blue reference text color between UI and NDI, and silencing the repeating mic watchdog chime.

## 1. Scripture Settings Mount Fix (Backgrounds Visibility)

### Issue
- The Bible backgrounds grid (`bgPreviewGrid`) and appearance controls are not displaying in the Appearance subtab.
- This is because `mountSidePanels()` in `ui/index.html` was designed to query-select `details.settings-advanced` to extract the appearance section. Since we unwrapped it and converted it into `<div class="vmix-steps" id="dispAppearanceSection">`, the query selector found nothing and the settings panel was empty.

### Proposed Fixes
- Update `mountSidePanels()` in `ui/index.html` to find `#dispAppearanceSection` directly by ID and append it to the `#panel-appearance` view.

## 2. Dynamic Vertical Position & Spacing Scales

### Objectives
- Let users decide the vertical alignment of the text block (Top, Center, Bottom) while keeping it centered horizontally.
- Allow users to decide the space between block lines (line gap scale) and English/French/Reference blocks (block gap scale).

### Proposed Fixes
- **Python Dataclass (`verse_display.py`):**
  - Add `vertical_position: str = "center"` to the `DisplaySettings` dataclass.
- **NDI Sender (`ndi_sender.py`):**
  - Read `disp.vertical_position` during `_render_frame`.
  - Calculate `y` based on alignment:
    - `"top"`: `pad_v + int(cfg.height * 0.05)`
    - `"bottom"`: `cfg.height - pad_v - total_h - int(cfg.height * 0.05)`
    - `"center"`: `pad_v + max(0, (cfg.height - 2 * pad_v - total_h) // 2)` (Default)
- **HTML UI (`ui/index.html`):**
  - Add a "Vertical Position" dropdown selection (`#dispVerticalPosition`) in settings.
  - Map `"dispVerticalPosition"` to `displaySettings.vertical_position` in the inputs registration loop.
  - Update `applyStageLayout(d, stageEl)` to dynamically set `stageEl.style.justifyContent` based on alignment (`flex-start`, `center`, `flex-end`), providing immediate visual vertical-alignment response in the browser.

## 3. Font Style & Color Parity (Blue Reference Text)

### Issue
- In NDI output, the book reference is rendered in a beautiful blue color (`(43, 155, 255)`, which is `#2b9bff`). In the browser UI, the reference was drawn with the standard text color (white/dark).
- This mismatch breaks visual parity between the app and the broadcast.

### Proposed Fixes
- Update `buildStageHtml(d)` in `ui/index.html` to render `.stage-ref` in `#2b9bff` (or `#0066cc` in light theme for readability) instead of using the custom text color.

## 4. Voice Commands Restoration

### Issue
- The user reported that "next verse" and "previous verse" voice commands are not working.
- This is because the speech recognition pipeline crashed and was not active, or because the bare/intent validation rules in `voice_commands.py` were too restrictive when nothing was initially on screen.

### Proposed Fixes
- Fix the repeating `mic_start_failed` crash loop (using our `self._mic_failed_warned` watchdog silence) so the voice engine can start and recover cleanly without hanging the app or audio context.
- Ensure the navigator properly loads and binds sequential indices when switching versions.

---

## 5. Verification & Testing

- **Appearance Tab:** Open the Settings -> Appearance tab and verify the backgrounds grid and text spacing controls are fully visible.
- **Vertical Alignment:** Select "Top" and "Bottom" and verify the text block moves vertically in both the UI preview and the NDI stream, while remaining centered horizontally.
- **Blue Reference:** Stage a verse and verify the Book reference is drawn in the identical blue color in both the UI and NDI output.
- **Voice Commands:** Press "Start Microphone" and say "next verse" or "previous verse" and verify it navigates cleanly.
