let currentVersion = null, currentLanguage = "English", secondaryLanguage = null;
let secondaryAbovePrimary = false;
let lastStageVerse = null;
let displaySettings = {
  theme: "dark", font_family: "serif", primary_bold: false, primary_italic: false,
  secondary_italic: true, show_border: false, ref_scale: 1, text_scale: 1,
  text_color: "#ffffff",
  background_mode: "solid", background_image: "",
  ref_position: "top", block_gap_scale: 1, line_gap_scale: 1,
  ref_color: "#2b9bff"
};
let backgroundImages = [];
let userPressedStart = false;

// Readability floors for the operator's stage box (col 3).
const MIN_STAGE_BODY_PX = 20;
const MIN_STAGE_REF_PX = 15;

function estimateWrappedLines(text, charsPerLine) {
  if (!text || !text.trim()) return 0;
  const words = text.split(/\s+/);
  let lines = 1, current = 0;
  for (const word of words) {
    const wlen = word.length;
    if (current && current + 1 + wlen > charsPerLine) {
      lines++; current = wlen;
    } else if (current) {
      current += 1 + wlen;
    } else {
      current = wlen;
    }
  }
  return Math.max(1, lines);
}

function getStageViewport() {
  const host = stage.parentElement || stage;
  const w = Math.max(200, (host.clientWidth || stage.clientWidth || 400) - 8);
  const h = Math.max(180, (host.clientHeight || stage.clientHeight || 300) - 8);
  return { w, h };
}

function computeStageLayout(d) {
  const { w: boxW, h: boxH } = getStageViewport();
  const ts = displaySettings.text_scale || 1;
  const rs = displaySettings.ref_scale || 1;
  const bgs = displaySettings.block_gap_scale || 1;
  const lgs = displaySettings.line_gap_scale || 1;
  const pLabel = d.primary_version_label || "[NKJV]";
  const sLabel = d.secondary_version_label || "[LSG]";
  const pFull = `${pLabel} ${d.text || ""}`.trim();
  const sFull = d.secondary_text ? `${sLabel} ${d.secondary_text}`.trim() : "";
  let body = Math.min(72, boxH * 0.095) * ts;
  let ref = body * 0.62 * rs;
  let lineGap = 6, blockGap = 10;
  const availH = boxH * 0.92;
  const availW = boxW * 0.96;
  const blockH = (n, px, lg) => n <= 0 ? 0 : n * px + Math.max(0, n - 1) * lg;
  for (let i = 0; i < 52; i++) {
    const cpl = Math.max(12, Math.floor(availW / Math.max(8, body * 0.52)));
    ref = Math.max(MIN_STAGE_REF_PX, body * 0.62 * rs);
    lineGap = Math.max(3, body * 0.30 * lgs);
    blockGap = Math.max(6, body * 0.40 * bgs);
    const pLines = estimateWrappedLines(pFull, cpl);
    const sLines = sFull ? estimateWrappedLines(sFull, cpl) : 0;
    let total = ref + blockGap + blockH(pLines, body, lineGap);
    if (sLines) total += blockGap + blockH(sLines, body, lineGap);
    if (total > availH) body = Math.max(MIN_STAGE_BODY_PX, body * 0.905);
    else if (total < availH * 0.86 && body < boxH * 0.12) body *= 1.05;
    else break;
  }
  const lh = 1 + lineGap / body;
  return { ref, body, lh, pFull, sFull };
}

// Shrinking stops at a size the operator can still read; anything longer
// than that scrolls in the stage box instead of turning into fine print.
function shrinkStageUntilFits(stageEl = stage) {
  const content = stageEl.querySelector(".stage-content");
  if (!content) return;
  for (let i = 0; i < 28; i++) {
    const overH = content.scrollHeight > stageEl.clientHeight + 2;
    const overW = content.scrollWidth > stageEl.clientWidth + 2;
    if (!overH && !overW) break;
    let shrank = false;
    content.querySelectorAll(".stage-ref, .stage-text, .stage-secondary").forEach(el => {
      const floor = el.classList.contains("stage-ref") ? MIN_STAGE_REF_PX : MIN_STAGE_BODY_PX;
      const px = parseFloat(getComputedStyle(el).fontSize) || 16;
      if (px <= floor) return;
      el.style.fontSize = Math.max(floor, px * 0.93) + "px";
      shrank = true;
    });
    if (!shrank) break;
  }
}

function applyStageLayout(d, stageEl = stage) {
  if (!stageEl) return;
  stageEl.classList.toggle("theme-light", displaySettings.theme === "light");
  stageEl.classList.toggle("bordered", !!displaySettings.show_border);
  stageEl.style.fontFamily = displaySettings.font_family === "sans" ? "var(--sans)" : "var(--serif)";
  
  const color = displaySettings.text_color || (displaySettings.theme === 'light' ? '#141418' : '#ffffff');
  stageEl.style.color = color;
  stageEl.style.backgroundColor = displaySettings.theme === "light" ? "rgba(255,255,255,0.94)" : "#141418";

  if (displaySettings.background_mode === "image" && displaySettings.background_image) {
    stageEl.style.backgroundImage = `url(/backgrounds/${encodeURIComponent(displaySettings.background_image)})`;
    stageEl.style.backgroundSize = "cover";
    stageEl.style.backgroundPosition = "center";
  } else {
    stageEl.style.backgroundImage = "";
    stageEl.style.backgroundSize = "";
  }

  const vPos = displaySettings.vertical_position || "center";
  if (vPos === "top") {
    stageEl.style.justifyContent = "safe flex-start";
  } else if (vPos === "bottom") {
    stageEl.style.justifyContent = "safe flex-end";
  } else {
    stageEl.style.justifyContent = "safe center";
  }
}

function buildStageHtml(d) {
  const lay = computeStageLayout(d);
  const refText = d.reference_display || `${d.book_french || ""} • ${d.book} ${d.chapter}:${d.verse}`.replace(/^ • /, "");
  const boldP = displaySettings.primary_bold ? "font-weight:bold;" : "";
  const italicP = displaySettings.primary_italic ? "font-style:italic;" : "";
  const italicS = displaySettings.secondary_italic ? "font-style:italic;" : "";
  
  const color = displaySettings.text_color || (displaySettings.theme === 'light' ? '#141418' : '#ffffff');
  const colorStyle = `color:${color};text-shadow:none;`; // Reset shadow if color is custom for better readability

  const refColor = displaySettings.ref_color || (displaySettings.theme === 'light' ? '#0052cc' : '#2b9bff');
  const refColorStyle = `color:${refColor};text-shadow:none;`;

  const refPos = displaySettings.ref_position || "top";
  const ref = `<div class="stage-ref" style="font-size:${lay.ref}px;${refColorStyle}">${refText}</div>`;
  const primary = `<div class="stage-text" style="font-size:${lay.body}px;line-height:${lay.lh};${boldP}${italicP}${colorStyle}">${lay.pFull}</div>`;
  if (!d.secondary_text) {
    if (refPos === "bottom") {
      return `<div class="stage-content">${primary}${ref}</div>`;
    }
    return `<div class="stage-content">${ref}${primary}</div>`;
  }
  const secClass = secondaryAbovePrimary ? "stage-secondary above" : "stage-secondary";
  const secondary = `<div class="${secClass}" style="font-size:${lay.body}px;line-height:${lay.lh};${italicS}${colorStyle}">${lay.sFull}</div>`;
  
  let blocks;
  if (refPos === "bottom") {
    blocks = secondaryAbovePrimary ? secondary + primary + ref : primary + secondary + ref;
  } else {
    blocks = secondaryAbovePrimary ? ref + secondary + primary : ref + primary + secondary;
  }
  return `<div class="stage-content">${blocks}</div>`;
}

// ── Stage / Live Output (col 3) + real pop-out projector window ──
function sendToStage(d) {
  lastStageVerse = d;
  const stages = [stage, $("browserStageLive")];
  stages.forEach(el => {
    if (!el) return;
    applyStageLayout(d, el);
    el.innerHTML = buildStageHtml(d);
    requestAnimationFrame(() => shrinkStageUntilFits(el));
  });
  liveDot.classList.add("on");
  liveTxt.textContent = "on air";
}
clearBtn.onclick = () => {
  clearStage();
};

function clearStage() {
  broadcastVerse = null;
  isOnAir = false;
  lastStageVerse = null;
  const stages = [stage, $("browserStageLive")];
  stages.forEach(el => {
    if (!el) return;
    el.innerHTML = `<div class="stage-empty">No verse on air</div>`;
    el.style.backgroundImage = "";
  });
  liveDot.classList.remove("on");
  liveTxt.textContent = "standby";
}

// ── Preview → Broadcast ──
// Nothing reaches the stage, the projector or NDI without going through
// broadcastFromPreview(); everything else only stages.
let previewVerse = null;
let broadcastVerse = null;
let browserPreviewVerse = null;
let isOnAir = false;

// Any click that stages a verse tells the server too, so the server's
// nav_state and the operator's screen can't disagree about what is staged.
function displayToPreview(d, { notifyServer = true } = {}) {
  if (!d) return;
  previewVerse = d;
  renderPreview(d);
  renderBrowserPreview(d);
  refBook.value = d.book || "";
  refChapter.value = d.chapter || "";
  refVerse.value = d.verse || "";
  addToRecall(d);
function renderPreview(d) {
  const containers = [$("stagePreview"), $("browserStagePreview")];
  if (!d) {
    previewVerse = null;
    containers.forEach(c => { if (c) c.innerHTML = `<div class="stage-empty">No verse staged</div>`; });
    return;
  }
  previewVerse = d;
  containers.forEach(c => {
    if (!c) return;
    applyStageLayout(d, c);
    c.innerHTML = buildStageHtml(d);
    requestAnimationFrame(() => shrinkStageUntilFits(c));
  });
}

function broadcastFromPreview(d) {
  const verse = d || previewVerse || browserPreviewVerse || null;
  renderPreview(d);

  renderBrowserPreview(d);
  sendToStage(d);
}

// Opens a REAL separate OS window -- drag it onto the projector/second
// display and fullscreen it (F11). Its title is fixed and distinctive so
// vMix's Local Desktop Capture can pick it out of the window list.
// In the desktop shell the projector is a second native window created by
// Python; window.open() there leaves the WebView2 sandbox and Windows hands
// the request to whatever claims http:// — the Microsoft Store on a machine
// with no default browser. The projector page talks to the backend directly,
// so it stays in sync without postMessage either way.
let projectorNative = false;

function openProjector() {
  if (window.pywebview && window.pywebview.api) {
    window.pywebview.api.open_projector().then(res => {
      if (res) {
        projectorNative = true;
        vmixWinDot.className = "dot on";
        vmixWinTxt.textContent = "Projector window: active";
      }
    });
  } else {
    // Fallback for browser testing
    const w = window.open("projector.html", "WindowVerseProjector", "width=1280,height=720");
    if (w) {
      projectorNative = true;
      vmixWinDot.className = "dot on";
      vmixWinTxt.textContent = "Projector window: active";
    } else {
function renderLibrary(msg) {
  currentVersion = msg.current_version;
  currentLanguage = msg.current_language || "English";
  secondaryLanguage = msg.secondary_language || null;
  if (typeof msg.secondary_above === "boolean") secondaryAbovePrimary = msg.secondary_above;

  if (versionPill && msg.versions) {
    versionPill.innerHTML = msg.versions.map(v => 
      `<option value="${v.version}" ${v.version === currentVersion ? "selected" : ""}>${v.version}</option>`
    ).join("");
    versionPill.value = currentVersion || "NKJV";
  }

  const selector = $("bibleVersionSelector");
  if (selector && msg.versions) {
    selector.innerHTML = msg.versions.map(v => 
      `<option value="${v.version}" ${v.version === currentVersion ? "selected" : ""}>${v.version}</option>`
    ).join("");
  }

  // The secondary translation is always on when a second language exists —
  // only its position above/below the primary is a choice.
  if (secondaryOrderRow) {
    secondaryOrderRow.style.display = secondaryLanguage ? "" : "none";
    if (secondaryLanguage) {
      if (secondaryOrderLang) secondaryOrderLang.textContent = secondaryLanguage;
      if (secondaryAbovePrimary) secondaryAbove.checked = true;
      else secondaryBelow.checked = true;
    }
  }
  if (lastStageVerse) sendToStage(lastStageVerse);
}

  if (msg.preview) renderPreview(msg.preview);
}
["dispTheme","dispFont","dispBold","dispItalic","dispSecItalic","dispBorder","dispTextScale","dispRefScale","dispBgMode","dispBgImage","dispTextColor","dispRefPosition","dispVerticalPosition","dispBlockGapScale","dispLineGapScale","dispRefColor"].forEach(id => {
  const el = $(id);
  if (!el) return;
  el.onchange = el.oninput = () => {
    const oldTheme = displaySettings.theme;
    displaySettings.theme = $("dispTheme")?.value || "dark";
    if (displaySettings.theme !== oldTheme) {
      // Auto-toggle colors on theme change
      const isLight = displaySettings.theme === "light";
      const txtColor = isLight ? "#000000" : "#ffffff";
      const refColor = isLight ? "#0052cc" : "#2b9bff";
      displaySettings.text_color = txtColor;
      displaySettings.ref_color = refColor;
      if ($("dispTextColor")) $("dispTextColor").value = txtColor;
      if ($("dispRefColor")) $("dispRefColor").value = refColor;
    } else {
      displaySettings.text_color = $("dispTextColor")?.value || "#ffffff";
      displaySettings.ref_color = $("dispRefColor")?.value || "#2b9bff";
    }
    displaySettings.font_family = $("dispFont")?.value || "serif";
    displaySettings.primary_bold = !!$("dispBold")?.checked;
    displaySettings.primary_italic = !!$("dispItalic")?.checked;
    displaySettings.secondary_italic = !!$("dispSecItalic")?.checked;
    displaySettings.show_border = !!$("dispBorder")?.checked;
    displaySettings.text_scale = parseFloat($("dispTextScale")?.value || "1");
    displaySettings.ref_scale = parseFloat($("dispRefScale")?.value || "1");
    displaySettings.background_mode = $("dispBgMode")?.value || "solid";
    displaySettings.background_image = $("dispBgImage")?.value || "";
    displaySettings.ref_position = $("dispRefPosition")?.value || "top";
    displaySettings.vertical_position = $("dispVerticalPosition")?.value || "center";
    displaySettings.block_gap_scale = parseFloat($("dispBlockGapScale")?.value || "1");
    displaySettings.line_gap_scale = parseFloat($("dispLineGapScale")?.value || "1");
    pushDisplaySettings();
  };
});
if ($("showJsonToggle")) {
  $("showJsonToggle").onchange = () => {
    $("settingsJsonPanel")?.classList.toggle("show", $("showJsonToggle").checked);
  };
}

function applyDisplayState(msg) {
  if (msg.settings) displaySettings = { ...displaySettings, ...msg.settings };
  if (msg.backgrounds) backgroundImages = msg.backgrounds;
  if (typeof displaySettings.ndi_output_enabled === "boolean") {
    ndiEnabled = displaySettings.ndi_output_enabled;
    if ($("ndiEnabledToggle")) $("ndiEnabledToggle").checked = ndiEnabled;
  }
  if ($("dispTheme")) $("dispTheme").value = displaySettings.theme || "dark";
  if ($("dispFont")) $("dispFont").value = displaySettings.font_family || "serif";
  if ($("dispBold")) $("dispBold").checked = !!displaySettings.primary_bold;
  if ($("dispItalic")) $("dispItalic").checked = !!displaySettings.primary_italic;
  if ($("dispSecItalic")) $("dispSecItalic").checked = displaySettings.secondary_italic !== false;
  if ($("dispBorder")) $("dispBorder").checked = !!displaySettings.show_border;
  if ($("dispTextScale")) $("dispTextScale").value = displaySettings.text_scale || 1;
  if ($("dispRefScale")) $("dispRefScale").value = displaySettings.ref_scale || 1;
  if ($("dispRefPosition")) $("dispRefPosition").value = displaySettings.ref_position || "top";
  if ($("dispBlockGapScale")) $("dispBlockGapScale").value = displaySettings.block_gap_scale || 1;
  if ($("dispLineGapScale")) $("dispLineGapScale").value = displaySettings.line_gap_scale || 1;
  if ($("dispBgMode")) $("dispBgMode").value = displaySettings.background_mode || "solid";
  if ($("dispTextColor")) $("dispTextColor").value = displaySettings.text_color || "#ffffff";
  if ($("dispRefColor")) $("dispRefColor").value = displaySettings.ref_color || "#2b9bff";
  if ($("dispBgImage")) {
    const grid = $("bgPreviewGrid");
    if (grid) {
      if (!backgroundImages || backgroundImages.length === 0) {
        grid.innerHTML = `<div style="padding:10px;color:var(--ink-40);font-size:12px">No backgrounds found in data/backgrounds/</div>`;
      } else {
        grid.innerHTML = backgroundImages.map(b => 
          `<div class="bg-thumb" data-bg="${b}" style="cursor:pointer;border:2px solid ${b===displaySettings.background_image?'var(--gold)':'transparent'}">
            <img src="/backgrounds/${encodeURIComponent(b)}" style="width:100%;height:60px;object-fit:cover;border-radius:4px" onerror="this.style.display='none'; this.parentElement.innerHTML='Error loading';">
           </div>`
        ).join("");
        grid.querySelectorAll(".bg-thumb").forEach(thumb => {
          thumb.onclick = () => {
            displaySettings.background_image = thumb.dataset.bg;
            displaySettings.background_mode = "image";
            $("dispBgMode").value = "image";
            pushDisplaySettings();
            grid.querySelectorAll(".bg-thumb").forEach(t => t.style.borderColor = "transparent");
            thumb.style.borderColor = "var(--gold)";
          };
        });
      }
    }
  }
  if (lastStageVerse) sendToStage(lastStageVerse);
}

const escapeHtml = s => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

function applyBrowserResults(msg) {
  const results = msg.results || [];
  browserVersesHdr.textContent = results.length
    ? `${results.length} result${results.length !== 1 ? "s" : ""} for "${msg.query}"`
    : `No results for "${msg.query}"`;
  renderBrowserVerseList(results);
  renderGridPane();
}

document.querySelectorAll("#testamentSeg .seg-btn").forEach(btn => {
  btn.onclick = () => {
    browserTestament = btn.dataset.testament;
    document.querySelectorAll("#testamentSeg .seg-btn")
      .forEach(b => b.classList.toggle("active", b === btn));
    renderBrowserBooks();
  };
});
if (browserBookFilter) browserBookFilter.oninput = renderBrowserBooks;
if (browserGridBack) browserGridBack.onclick = gridPaneBack;
document.querySelectorAll("#bookViewSeg .seg-btn").forEach(btn => {
  btn.onclick = () => {
    bookView = btn.dataset.bookview;
    document.querySelectorAll("#bookViewSeg .seg-btn")
      .forEach(b => b.classList.toggle("active", b === btn));
    renderBrowserBooks();
  };
});
if (browserBroadcastBtn) browserBroadcastBtn.onclick = () => broadcastFromPreview();
renderPreview(null);
initColumnDrag();
initLayoutResize();
const ndiEnabledToggle = $("ndiEnabledToggle");
if (ndiEnabledToggle) {
        if (!msg.on_air) clearStage();
      }
      if (typeof msg.opacity === "number" && stage) {
        stage.style.opacity = String(msg.opacity);
      }
      if (typeof msg.secondary_above === "boolean") {
        secondaryAbovePrimary = msg.secondary_above;
        if (secondaryAbove) secondaryAbove.checked = msg.secondary_above;
        if (secondaryBelow) secondaryBelow.checked = !msg.secondary_above;
        if (lastStageVerse) sendToStage(lastStageVerse);
      }
      break;
    case "ndi_preview_sent":
      if (ndiPreviewStatus) ndiPreviewStatus.textContent = "Test verse sent — check vMix NDI input now.";
      sendToStage({
        book: "John", chapter: 3, verse: 16,
        text: "For God so loved the world, that he gave his only begotten Son.",
        secondary_text: secondaryLanguage
          ? `[${secondaryLanguage} sample] Car Dieu a tant aimé le monde qu'il a donné son Fils unique.`
          : null,
      });
      break;
    case "mic_startup_progress":
      if (micProgressBar) micProgressBar.style.width = (msg.percent || 0) + "%";
      if (micProgress) micProgress.classList.add("show");
      break;
    case "system_log":
      if (!userPressedStart && (msg.level === "error" || msg.level === "warn")) {
        if (msg.code === "matched_reference_missing_from_db") {
          vmixDbDot.className = "dot bad";
          vmixDbTxt.textContent = "Bible DB: missing row for last reference";
        }
        break;
      }
      appendSystemLog(msg);
      if (msg.code === "transcript_saved") {
        const auto = /auto-save/i.test(msg.message || "");
        const secs = Math.round(silenceSaveSeconds || 0);
      renderPreview(null);
      renderBrowserPreview(null);
      break;
    case "nav_state":
      applyNavState(msg);
      break;
    case "voice_command":
      applyDisplayState(msg);
      break;
    case "detection_state":
      applyDetectionState(msg);
      break;
    case "voice_keywords":
      renderVoiceKeywords(msg);
      break;
    case "audio_devices":