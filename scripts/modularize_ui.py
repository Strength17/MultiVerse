"""
modularize_ui.py
Automated high-fidelity script to refactor monolithic ui/index.html into highly-engineered,
modular, and maintainable CSS and JS files grouped by logical module.
"""
from pathlib import Path
import re

def main():
    root = Path(__file__).parent.parent
    index_path = root / "ui" / "index.html"
    
    if not index_path.exists():
        print(f"Error: {index_path} not found.")
        return

    content = index_path.read_text(encoding="utf-8")
    
    # Create target directories
    css_dir = root / "ui" / "css"
    js_dir = root / "ui" / "js"
    css_dir.mkdir(parents=True, exist_ok=True)
    js_dir.mkdir(parents=True, exist_ok=True)
    
    # ── 1. EXTRACT CSS STYLES ──
    # Style block is between the first <style> and </style>
    style_match = re.search(r"<style>(.*?)</style>", content, re.DOTALL)
    if not style_match:
        print("Error: Style tag not found.")
        return
        
    full_css = style_match.group(1).strip()
    
    # Split CSS into modules:
    # onboarding.css: starts at /* ── Onboarding Screen ──
    onboarding_css_marker = "/* ── Onboarding Screen ────────────────────────────────────────────── */"
    if onboarding_css_marker in full_css:
        css_parts = full_css.split(onboarding_css_marker, 1)
        general_css = css_parts[0].strip()
        onboarding_css = onboarding_css_marker + "\n" + css_parts[1].strip()
    else:
        general_css = full_css
        onboarding_css = ""

    # Split general_css into main.css and panels.css
    # Let's separate panels, grids, columns, sidebar settings into panels.css
    panels_marker = "/* ──"
    # We can also search for .grid, .column, .vmix, .browser, etc.
    main_css_lines = []
    panels_css_lines = []
    
    in_panels = False
    for line in general_css.splitlines():
        # Check if line contains section header related to layout panels
        if any(keyword in line for keyword in ["Workspace Grid", "Columns", "vmix-steps", "Browser Panel", "Settings Layout"]):
            in_panels = True
        elif any(keyword in line for keyword in ["Base Variables", "Reset", "Typography", "Buttons", "Toasts"]):
            in_panels = False
            
        if in_panels:
            panels_css_lines.append(line)
        else:
            main_css_lines.append(line)
            
    main_css = "\n".join(main_css_lines).strip()
    panels_css = "\n".join(panels_css_lines).strip()
    
    # Write CSS files
    (css_dir / "main.css").write_text(main_css, encoding="utf-8")
    (css_dir / "panels.css").write_text(panels_css, encoding="utf-8")
    (css_dir / "onboarding.css").write_text(onboarding_css, encoding="utf-8")
    
    print("CSS files modularized successfully!")

    # ── 2. EXTRACT JS CODE ──
    # JS code is inside the main <script> tag at the end of the file.
    # Note: there is also an appLoadingOverlay script inline, but we want the main script.
    # We find the main <script> tag which ends right before </script>\n</body>
    script_matches = list(re.finditer(r"<script>(.*?)</script>", content, re.DOTALL))
    if not script_matches:
        print("Error: Script tags not found.")
        return
        
    # The last script block is the main one
    main_script_content = script_matches[-1].group(1).strip()
    
    # Split JS content into clean modules line-by-line
    utils_lines = []
    websocket_lines = []
    onboarding_lines = []
    navigation_lines = []
    settings_lines = []
    app_lines = []
    
    # Let's classify variables and functions based on their purpose:
    # 1. UTILS (helpers, meter, clipboard, toast)
    # 2. WEBSOCKET (ws, connectWs, wsSend, onWsMessage)
    # 3. ONBOARDING (onboarding step controller, indicator updates)
    # 4. NAVIGATION (resolve, renderPreview, clearStage, etc.)
    # 5. SETTINGS (mountSidePanels, settings bindings)
    # 6. APP (app launch, DOM event listeners, global states, main loop)
    
    js_lines = main_script_content.splitlines()
    
    current_module = "app" # Default fallback
    
    # We will group specific global variables and functions into files
    i = 0
    while i < len(js_lines):
        line = js_lines[i]
        stripped = line.strip()
        
        # Simple classification routing
        if "Onboarding & Setup" in line:
            current_module = "onboarding"
        elif "wsSend" in line or "connectWs" in line or "onWsMessage" in line or "WebSocket" in line:
            current_module = "websocket"
        elif "renderPreview" in line or "clearStage" in line or "applyDisplayState" in line or "drawVMMeter" in line:
            current_module = "navigation"
        elif "mountSidePanels" in line or "renderAudioDevices" in line:
            current_module = "settings"
        elif "copyTextToClipboard" in line or "showToast" in line or "const $ =" in line:
            current_module = "utils"
            
        # Specific routing overrides for functions
        if stripped.startswith("function ") or stripped.startswith("const ") or stripped.startswith("let "):
            name = ""
            m = re.match(r"(function|const|let|var)\s+([\w\$]+)", stripped)
            if m:
                name = m.group(2)
                
            if name in ["$", "showToast", "copyTextToClipboard", "formatStartupMessage"]:
                current_module = "utils"
            elif name in ["ws", "connectWs", "wsSend", "onWsMessage", "scheduleReconnect", "reconnectTimer", "reconnectAttempts"]:
                current_module = "websocket"
            elif name in ["currentOnboardingStep", "totalOnboardingSteps", "verifiedOnboardingTranscription", "showOnboardingStep", "handleRequirementsStatus", "handleOnboardingTranscript", "initOnboarding"]:
                current_module = "onboarding"
            elif name in ["renderPreview", "clearStage", "applyDisplayState", "applyBrowserResults", "renderLibrary", "renderActiveVerse", "currentVersion", "currentLanguage", "autoDisplayTimer", "stagePreview"]:
                current_module = "navigation"
            elif name in ["mountSidePanels", "renderAudioDevices", "renderVoiceKeywords", "selectedMic", "audioDevices"]:
                current_module = "settings"
            elif name in ["backendReady", "structureRequested", "voiceKeywordsRequested", "lastSpeechActivityAt", "searchInput"]:
                current_module = "app"

        # Append to respective module lists
        if current_module == "utils":
            utils_lines.append(line)
        elif current_module == "websocket":
            websocket_lines.append(line)
        elif current_module == "onboarding":
            onboarding_lines.append(line)
        elif current_module == "navigation":
            navigation_lines.append(line)
        elif current_module == "settings":
            settings_lines.append(line)
        else:
            app_lines.append(line)
            
        i += 1

    # Write JS Files
    (js_dir / "utils.js").write_text("\n".join(utils_lines).strip(), encoding="utf-8")
    (js_dir / "websocket.js").write_text("\n".join(websocket_lines).strip(), encoding="utf-8")
    (js_dir / "onboarding.js").write_text("\n".join(onboarding_lines).strip(), encoding="utf-8")
    (js_dir / "navigation.js").write_text("\n".join(navigation_lines).strip(), encoding="utf-8")
    (js_dir / "settings.js").write_text("\n".join(settings_lines).strip(), encoding="utf-8")
    (js_dir / "app.js").write_text("\n".join(app_lines).strip(), encoding="utf-8")
    
    print("JS files modularized successfully!")

    # ── 3. REWRITE INDEX.HTML ──
    # Create the beautiful modular HTML skeleton
    # Let's extract the HTML skeleton by keeping everything except <style>...</style> and the main <script>...</script> block.
    
    # We replace the style block with stylesheet links
    skeleton = content
    skeleton = re.sub(r"<style>.*?</style>", 
                      '<!-- Modular Stylesheets -->\n'
                      '  <link rel="stylesheet" href="css/main.css">\n'
                      '  <link rel="stylesheet" href="css/panels.css">\n'
                      '  <link rel="stylesheet" href="css/onboarding.css">', 
                      skeleton, flags=re.DOTALL)
                      
    # We replace the main script block with module scripts
    # Find the main script block at the end (the last one inside the file)
    last_script_start = skeleton.rfind("<script>")
    last_script_end = skeleton.rfind("</script>")
    
    if last_script_start != -1 and last_script_end != -1:
        script_links = (
            '<!-- Modular JS Architecture -->\n'
            '  <script src="js/utils.js" defer></script>\n'
            '  <script src="js/websocket.js" defer></script>\n'
            '  <script src="js/onboarding.js" defer></script>\n'
            '  <script src="js/navigation.js" defer></script>\n'
            '  <script src="js/settings.js" defer></script>\n'
            '  <script src="js/app.js" defer></script>'
        )
        skeleton = skeleton[:last_script_start] + script_links + skeleton[last_script_end + len("</script>"):]

    index_path.write_text(skeleton, encoding="utf-8")
    print("ui/index.html rewritten successfully!")

if __name__ == "__main__":
    main()
