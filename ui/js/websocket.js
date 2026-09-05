let ws = null;
let reconnectTimer = null;
let logCount = 0;
let ndiEnabled = true;
let toastTimer = null;
  wsSend({ action: "clear_broadcast" });
  if (notifyServer) wsSend({ action: "stage_preview", verse: d });
}

  wsSend({ action: "broadcast_verse", verse });
}

function markOnAir(d) {
  broadcastVerse = d;
  isOnAir = true;
  
  // Keep the live verse in the preview box as well so it never disappears!
  previewVerse = d;
      chip.onclick = () => wsSend({
        action: "set_voice_keywords", op: entry.enabled ? "disable" : "enable",
        intent: group.intent, phrase: entry.phrase,
      });
      chips.appendChild(chip);
    }
    for (const phrase of group.custom || []) {
      const chip = document.createElement("span");
      chip.className = "kw-chip on custom";
      chip.textContent = phrase;
      const x = document.createElement("span");
      x.className = "x";
      x.innerHTML = iconSvg("x", 12);
      chip.appendChild(x);
      chip.title = "Remove this phrase";
      chip.onclick = () => wsSend({
        action: "set_voice_keywords", op: "remove",
        intent: group.intent, phrase,
      });
      chips.appendChild(chip);
    }
    block.appendChild(chips);

    const add = document.createElement("div");
    add.className = "kw-add";
    const input = document.createElement("input");
    input.className = "search-input";
    input.placeholder = `Add a phrase for "${VOICE_INTENT_LABELS[group.intent] || group.intent}"…`;
    const btn = document.createElement("button");
    btn.className = "btn small";
    btn.textContent = "Add";
    const submit = () => {
      const phrase = input.value.trim();
      if (!phrase) return;
      input.value = "";
      wsSend({ action: "set_voice_keywords", op: "add", intent: group.intent, phrase });
    };
    btn.onclick = submit;
    input.onkeydown = e => { if (e.key === "Enter") submit(); };
    add.append(input, btn);
    block.appendChild(add);
    host.appendChild(block);
  }
}

// ── JSON log ──
function colorJson(str) {
  return str
    .replace(/"([^"]+)":/g, '<span class="jk">"$1"</span>:')
    .replace(/: "([^"]*)"/g, ': <span class="js">"$1"</span>')
    .replace(/: (true|false)/g, ': <span class="jb">$1</span>')
    .replace(/: (-?\d+\.?\d*)/g, ': <span class="jn">$1</span>');
}
function appendJson(obj) {
  const raw = JSON.stringify(obj);
  const html = colorJson(raw);
  [jsonFeed, $("jsonFeedSettings")].forEach(el => {
    if (!el) return;
    const div = document.createElement("div");
    div.className = "json-row";
    div.dataset.raw = raw;
    div.innerHTML = html;
    el.prepend(div);
    while (el.childElementCount > 100) el.removeChild(el.lastChild);
  });
}

function copyJsonLog() {
  const rows = [...document.querySelectorAll("#jsonFeedSettings .json-row, #jsonFeed .json-row")];
  const text = rows.map(r => r.dataset.raw || r.textContent).reverse().join("\n");
function wsSend(payload) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(payload));
    return true;
  }
  wsSend({ action: "set_secondary_order", above });
  if (lastStageVerse) sendToStage(lastStageVerse);
}
if (secondaryBelow) secondaryBelow.onchange = onSecondaryOrderChange;
if (secondaryAbove) secondaryAbove.onchange = onSecondaryOrderChange;
if (ndiPreviewBtn) {
  ndiPreviewBtn.onclick = () => {
    wsSend({ action: "ndi_preview" });
    if (ndiPreviewStatus) ndiPreviewStatus.textContent = "Sending test verse to NDI…";
  };
}

const micSelect = $("micSelect");
if (micSelect) micSelect.onchange = () => wsSend({ action: "set_mic", name: micSelect.value });

const bibleVersionSelector = $("bibleVersionSelector");
if (bibleVersionSelector) bibleVersionSelector.onchange = () => wsSend({ action: "switch_version", version: bibleVersionSelector.value });
if (versionPill) versionPill.onchange = () => wsSend({ action: "switch_version", version: versionPill.value });

function applyDisplaySettingsToAllStages() {
  const stages = [stage, $("stagePreview"), $("browserStagePreview"), $("browserStageLive")];
  stages.forEach(el => {
    if (!el) return;
    const isLive = el === stage || el === $("browserStageLive");
    const d = isLive ? lastStageVerse : previewVerse;
    applyStageLayout(d || {}, el);
    if (d) {
      el.innerHTML = buildStageHtml(d);
      requestAnimationFrame(() => shrinkStageUntilFits(el));
    } else {
      el.innerHTML = isLive ? `<div class="stage-empty">No verse on air</div>` : `<div class="stage-empty">No verse staged</div>`;
    }
  });
}

function pushDisplaySettings() {
  wsSend({ action: "set_display", settings: displaySettings });
  applyDisplaySettingsToAllStages();
}

const NARRATIVE_PRESETS = {
  1: { label: "Strict", hint: "Fewest false triggers — needs clear story wording." },
  2: { label: "Moderate", hint: "Conservative — good for mixed sermon and announcements." },
  3: { label: "Balanced", hint: "Recommended default — real stories without casual chatter." },
  4: { label: "Sensitive", hint: "Catches shorter retellings — may occasionally misfire." },
  5: { label: "Very sensitive", hint: "Most forgiving — use only if stories are still missed." },
};
let narrativeSensitivity = 3;
let searchTestamentFilter = "all";
let silenceSaveSeconds = 10;

function pushDetectionSettings(patch) {
  wsSend({ action: "set_detection", ...patch });
}

function updateSearchTestamentUI(value) {
  searchTestamentFilter = (value || "all").toLowerCase();
  if (searchTestament) searchTestament.value = searchTestamentFilter;
  const settingsSel = $("settingsSearchTestament");
  if (settingsSel) settingsSel.value = searchTestamentFilter;
}

function updateSilenceSaveUI(seconds, preset) {
  silenceSaveSeconds = Math.max(5, Math.min(600, parseFloat(seconds) || 10));
  const presetSel = $("silenceSavePreset");
  const customRow = $("silenceSaveCustomRow");
  const customInput = $("silenceSaveCustom");
  const presets = ["10", "20", "30", "60", "120"];
  let chosen = preset;
  if (!chosen) {
    chosen = presets.find(p => Math.abs(parseFloat(p) - silenceSaveSeconds) < 0.5) ? String(Math.round(silenceSaveSeconds)) : "custom";
  }
  if (presetSel) presetSel.value = chosen === String(Math.round(silenceSaveSeconds)) && presets.includes(chosen) ? chosen : (presets.includes(String(Math.round(silenceSaveSeconds))) ? String(Math.round(silenceSaveSeconds)) : "custom");
  if (customInput) customInput.value = String(Math.round(silenceSaveSeconds));
  if (customRow) customRow.style.display = (presetSel && presetSel.value === "custom") ? "block" : "none";
}

function sendDetectionSettings() {
  pushDetectionSettings({
    narrative_sensitivity: narrativeSensitivity,
    search_testament: searchTestamentFilter,
    silence_save_seconds: silenceSaveSeconds,
  });
}

// Search is a lookup tool, not a broadcast trigger: it shows a handful of
// matches inline, sends the rest to the Scripture Browser, and a click
// only ever stages a verse for Preview.
const SEARCH_INLINE_LIMIT = 3;
let lastSearchQuery = "";

function renderSearchResults(msg) {
  if (!searchResults) return;
  searchResults.innerHTML = "";
  lastSearchQuery = msg.query || "";
  const all = msg.results || [];
  if (!all.length) {
    searchResults.appendChild(Object.assign(document.createElement("div"), {
      className: "search-empty",
      textContent: `No matches found for "${msg.query || ""}". Try different wording or All Bible.`,
    }));
    resetDockHeight();
    return;
  }

  const count = document.createElement("div");
  count.className = "search-group-hdr";
  count.textContent = `${all.length} match${all.length !== 1 ? "es" : ""}`;
  searchResults.appendChild(count);

  // A short result set is worth reading in place; a long one would bury the
  // stage, so it stays a count plus a way into the browser.
  if (all.length <= SEARCH_INLINE_LIMIT) {
    for (const hit of all) searchResults.appendChild(buildSearchRow(hit));
  }
  const open = document.createElement("button");
  open.className = "btn small search-open-browser";
  open.textContent = all.length <= SEARCH_INLINE_LIMIT
    ? "Open all in Scripture Browser →"
    : `See all ${all.length} verses in Scripture Browser →`;
  open.onclick = () => openSearchInBrowser(msg.query || "", msg.testament);
  searchResults.appendChild(open);
  fitDockToSearch();
}

// The dock grows to fit what the search actually returned (and shrinks back
// afterwards) so results are never hidden behind their own scrollbar, while
// the columns above just give up the space they no longer need.
function fitDockToSearch() {
  if (!liveBottomDock) return;
  const section = searchResults?.closest(".dock-section");
  if (!section) return;
  requestAnimationFrame(() => {
    const chrome = section.clientHeight - searchResults.clientHeight;
    const wanted = chrome + searchResults.scrollHeight + 8;
    const max = Math.round(window.innerHeight * 0.5);
    const floor = Math.max(DOCK_MIN_HEIGHT, dockBaseHeight());
    liveBottomDock.style.height =
      Math.round(Math.min(max, Math.max(floor, wanted))) + "px";
  });
}

// Back to whatever height the operator last chose (or the default) once the
// results no longer need the extra room.
function resetDockHeight() {
  if (liveBottomDock) liveBottomDock.style.height = dockBaseHeight() + "px";
}

function buildSearchRow(hit) {
  const row = document.createElement("div");
  row.className = "search-hit";
  const pct = Math.round((hit.confidence || 0) * 100);
  const type = (hit.match_type || hit.source || "match").replace(/_/g, " ");
  
  const content = document.createElement("div");
  content.style.flex = "1";
  content.innerHTML = `
    <div class="search-hit-ref">${hit.book} ${hit.chapter}:${hit.verse}</div>
    <div class="search-hit-text">${hit.text || ""}</div>
    <div class="search-hit-meta">${type}${pct ? ` · ${pct}%` : ""}</div>`;
  
  const displayBtn = document.createElement("button");
  displayBtn.className = "btn small start";
  displayBtn.style.padding = "4px 8px";
  displayBtn.innerHTML = iconSvg("broadcast", 12);
  displayBtn.title = "Display this verse directly";
  displayBtn.onclick = (e) => {
    e.stopPropagation();
    broadcastFromPreview(hit);
  };

  row.style.display = "flex";
  row.style.alignItems = "center";
  row.style.gap = "8px";
  row.append(content, displayBtn);
  
  row.onclick = () => displayToPreview({ ...hit, source: "search" });
  return row;
}

function openSearchInBrowser(query, testament) {
  showView("scripture");
  wsSend({
    action: "load_search_results",
    query: query || lastSearchQuery,
    testament: testament || searchTestamentFilter || "all",
  });
}

function updateNarrativeSensitivityUI(level) {
  narrativeSensitivity = Math.max(1, Math.min(5, parseInt(level, 10) || 3));
  const preset = NARRATIVE_PRESETS[narrativeSensitivity] || NARRATIVE_PRESETS[3];
  const slider = $("narrativeSensitivity");
  if (slider) slider.value = String(narrativeSensitivity);
  if ($("narrativeSensitivityLabel")) $("narrativeSensitivityLabel").textContent = preset.label;
  if ($("narrativeSensitivityHint")) $("narrativeSensitivityHint").textContent = preset.hint;
}

const narrativeSlider = $("narrativeSensitivity");
if (narrativeSlider) {
  narrativeSlider.oninput = () => {
    updateNarrativeSensitivityUI(narrativeSlider.value);
    sendDetectionSettings();
  };
}

const settingsSearchTestament = $("settingsSearchTestament");
if (settingsSearchTestament) {
  settingsSearchTestament.onchange = () => {
    updateSearchTestamentUI(settingsSearchTestament.value);
    sendDetectionSettings();
  };
}
if (searchTestament) {
  searchTestament.onchange = () => {
    updateSearchTestamentUI(searchTestament.value);
    sendDetectionSettings();
  };
}

const silenceSavePreset = $("silenceSavePreset");
const silenceSaveCustom = $("silenceSaveCustom");
function syncSilenceFromPreset() {
  if (!silenceSavePreset) return;
  if (silenceSavePreset.value === "custom") {
    updateSilenceSaveUI(parseFloat(silenceSaveCustom?.value || "10"), "custom");
  } else {
    updateSilenceSaveUI(parseFloat(silenceSavePreset.value), silenceSavePreset.value);
  }
  sendDetectionSettings();
}
if (silenceSavePreset) silenceSavePreset.onchange = syncSilenceFromPreset;
if (silenceSaveCustom) {
  silenceSaveCustom.onchange = () => {
    updateSilenceSaveUI(parseFloat(silenceSaveCustom.value), "custom");
    sendDetectionSettings();
  };
}

function applyDetectionState(msg) {
  if (!msg.settings) return;
  if (typeof msg.settings.narrative_sensitivity === "number") {
    updateNarrativeSensitivityUI(msg.settings.narrative_sensitivity);
  } else if (msg.settings.narrative_label) {
    updateNarrativeSensitivityUI(narrativeSensitivity);
    if ($("narrativeSensitivityLabel")) $("narrativeSensitivityLabel").textContent = msg.settings.narrative_label;
    if ($("narrativeSensitivityHint")) $("narrativeSensitivityHint").textContent = msg.settings.narrative_hint || "";
  }
  if (msg.settings.search_testament) updateSearchTestamentUI(msg.settings.search_testament);
  if (typeof msg.settings.silence_save_seconds === "number") {
    updateSilenceSaveUI(msg.settings.silence_save_seconds, msg.settings.silence_save_preset);
  }
  for (const [id, key] of Object.entries(VOICE_TOGGLES)) {
    if (typeof msg.settings[key] === "boolean" && $(id)) $(id).checked = msg.settings[key];
  }
  syncVoiceNavOptions();
}

// The sub-options only make sense while the master switch is on.
function syncVoiceNavOptions() {
  const on = !!$("voiceNavEnabled")?.checked;
  $("voiceNavOptions")?.classList.toggle("disabled", !on);
  if (on && !voiceKeywordsRequested && ws && ws.readyState === WebSocket.OPEN) {
    voiceKeywordsRequested = wsSend({ action: "get_voice_keywords" });
  }
}
    wsSend({ action: "set_voice_nav", [key]: el.checked });
    if (id === "voiceNavEnabled") syncVoiceNavOptions();
  };
});
syncVoiceNavOptions();

function applyNavState(msg) {
  const ref = msg.reference;
  if (ref && document.activeElement !== refBook) {
    refBook.value = ref.book || "";
    refChapter.value = ref.chapter || "";
    refVerse.value = ref.verse || "";
  }
  if (navPrevBtn) navPrevBtn.disabled = !msg.has_prev;
  if (navNextBtn) navNextBtn.disabled = !msg.has_next;
  if (stagePrevBtn) stagePrevBtn.disabled = !msg.has_prev;
  if (stageNextBtn) stageNextBtn.disabled = !msg.has_next;
  if (browserPrevBtn) browserPrevBtn.disabled = !msg.has_prev;
  if (browserNextBtn) browserNextBtn.disabled = !msg.has_next;
  isOnAir = !!msg.on_air;
  // nav_state is a status echo, not a command: it must never wipe what the
  // operator staged. Only preview_cleared empties the strip.
      wsSend({ action: "set_mic", name: selectedMic });
    wsSend({ action: "get_audio_devices" });
});

// ── Scripture Browser ────────────────────────────────────────────────
// Book/chapter/verse structure comes from the backend (the active Bible
// file is the authority on what exists), never from a hardcoded table.
let bibleBooks = [];
let browserTestament = "all";
let browserBook = null, browserChapter = null;
  if (structureRequested || !ws || ws.readyState !== WebSocket.OPEN) return;
  structureRequested = true;
  wsSend({ action: "get_bible_structure", testament: "all" });
}

function applyBibleStructure(msg) {
  bibleBooks = msg.books || [];
  if (bookOptions) {
    bookOptions.innerHTML = "";
    for (const b of bibleBooks) {
      const opt = document.createElement("option");
      opt.value = b.book;
      bookOptions.appendChild(opt);
    }
  }
  renderBrowserBooks();
}

function visibleBooks() {
  const filter = (browserBookFilter?.value || "").trim().toLowerCase();
  return bibleBooks.filter(b =>
    (browserTestament === "all" || (b.testament || "").toLowerCase() === browserTestament) &&
    (!filter || b.book.toLowerCase().includes(filter) ||
      (b.abbrev || "").toLowerCase().includes(filter)));
}

function renderBrowserBooks() {
  if (!browserBooks) return;
  browserBooks.innerHTML = "";
  browserBooks.className = bookView === "grid" ? "book-grid" : "browser-list";
  const shown = visibleBooks();
  if (!shown.length) {
    browserBooks.innerHTML = `<div class="browser-empty">No books match</div>`;
    return;
  }
  for (const b of shown) {
    const cell = document.createElement("div");
    const active = browserBook === b.book_number;
    if (bookView === "grid") {
      cell.className = "chapter-cell book-cell" + (active ? " active" : "");
      cell.textContent = b.abbrev || b.book.slice(0, 3);
      cell.title = b.book;
    } else {
      cell.className = "browser-row" + (active ? " active" : "");
      cell.textContent = b.book;
    }
    cell.onclick = () => selectBrowserBook(b.book_number);
    browserBooks.appendChild(cell);
  }
  if (gridMode === "books") renderGridPane();
}

// The middle pane walks books -> chapters -> verses in place, so the last
// click in it is always the actual verse rather than a dead end at chapters.
function renderGridPane() {
  if (!browserChapters) return;
  browserChapters.innerHTML = "";
  browserChapters.className = "chapter-grid" + (gridMode === "books" ? " books" : "");
  if (browserGridBack) browserGridBack.style.display = gridMode === "books" ? "none" : "";
  const bookName = (bibleBooks.find(b => b.book_number === browserBook) || {}).book || "";

  if (gridMode === "books") {
    if (browserGridHdr) browserGridHdr.textContent = "Books";
    for (const b of visibleBooks()) {
      const cell = document.createElement("div");
      cell.className = "chapter-cell book-cell" + (browserBook === b.book_number ? " active" : "");
      cell.textContent = b.abbrev || b.book.slice(0, 3);
      cell.title = b.book;
      cell.onclick = () => selectBrowserBook(b.book_number);
      browserChapters.appendChild(cell);
    }
    return;
  }

  if (gridMode === "chapters") {
    if (browserGridHdr) browserGridHdr.textContent = `${bookName} — chapters`;
    for (const ch of gridChapters) {
      const cell = document.createElement("div");
      cell.className = "chapter-cell" + (ch === browserChapter ? " active" : "");
      cell.textContent = ch;
      cell.onclick = () => {
        gridMode = "verses";
        wsSend({ action: "get_chapter", book_number: browserBook, chapter: ch });
      };
      browserChapters.appendChild(cell);
    }
    return;
  }

  if (browserGridHdr) browserGridHdr.textContent = `${bookName} ${browserChapter} — verses`;
  for (const v of gridVerses) {
    const cell = document.createElement("div");
    cell.className = "chapter-cell" + (browserPreviewVerse
      && browserPreviewVerse.verse === v.verse
      && browserPreviewVerse.chapter === browserChapter ? " active" : "");
    cell.textContent = v.verse;
    cell.onclick = () => {
      // 1. Update active verse selection
      displayToPreview({ ...v, source: "browser" });
      renderGridPane();
      
      // 2. Scroll to and highlight in verse list
      const verseRow = Array.from(browserVerses.querySelectorAll(".browser-row")).find(
        row => row.dataset.verse === String(v.verse)
      );
      if (verseRow) {
        browserVerses.querySelectorAll(".browser-row").forEach(r => r.classList.remove("active"));
        verseRow.classList.add("active");
        verseRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    };
    browserChapters.appendChild(cell);
  }
}

function gridPaneBack() {
  if (gridMode === "verses") gridMode = "chapters";
  else if (gridMode === "chapters") gridMode = "books";
  renderGridPane();
}

function selectBrowserBook(bookNumber, chapter) {
  browserBook = bookNumber;
  gridMode = chapter ? "verses" : "chapters";
  renderBrowserBooks();
  wsSend({ action: "get_chapter", book_number: bookNumber, chapter: chapter || 1 });
}

function applyChapterVerses(msg) {
  browserBook = msg.book_number;
  browserChapter = msg.chapter;
  renderBrowserBooks();

  gridChapters = msg.chapters || [];
  gridVerses = msg.verses || [];
  if (gridMode === "books") gridMode = "chapters";
  renderGridPane();

  browserVersesHdr.textContent = `${msg.book} ${msg.chapter}`;
  renderBrowserVerseList(msg.verses || []);
}

function renderBrowserVerseList(verses) {
  browserVerses.innerHTML = "";
  if (!verses.length) {
    browserVerses.innerHTML = `<div class="browser-empty">No verses here</div>`;
    return;
  }
  for (const v of verses) {
    const row = document.createElement("div");
    row.className = "browser-row";
    row.dataset.verse = v.verse;
    
    const content = document.createElement("div");
    content.style.flex = "1";
    content.innerHTML = `<span class="browser-verse-num">${v.verse}</span>${v.text || ""}`;
    
    const displayBtn = document.createElement("button");
    displayBtn.className = "btn small start";
    displayBtn.style.padding = "4px 8px";
    displayBtn.innerHTML = iconSvg("broadcast", 12);
    displayBtn.title = "Display this verse directly";
    displayBtn.onclick = (e) => {
      e.stopPropagation();
      broadcastFromPreview(v);
    };

    row.style.display = "flex";
    row.style.alignItems = "center";
    row.style.gap = "8px";
    row.append(content, displayBtn);
    
    row.onclick = () => {
      browserVerses.querySelectorAll(".browser-row").forEach(r => r.classList.remove("active"));
      row.classList.add("active");
      row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      displayToPreview({ ...v, source: "browser" }); // This now just stages to preview
    };
    browserVerses.appendChild(row);
  }
}

// Live update stage text color from picker
$("dispTextColor").oninput = (e) => {
  stage.style.color = e.target.value;
  // Apply to primary and secondary too for consistency
  stage.querySelectorAll(".stage-text, .stage-secondary, .stage-ref").forEach(el => {
    if (el.classList.contains("stage-ref")) return; // Keep ref color or override as needed
    el.style.color = e.target.value;
  });
};

function renderBrowserPreview(d) {
  browserPreviewVerse = d || null;
  if (!browserPreview) return;
  if (!d) {
    browserPreview.innerHTML = `<div class="browser-empty">Select a verse to preview it here</div>`;
    return;
  }
  const sec = d.secondary_text ? `<div class="sec">${d.secondary_text}</div>` : "";
  browserPreview.innerHTML =
    `<div class="ref">${d.book} ${d.chapter}:${d.verse}</div><div>${d.text || ""}</div>${sec}`;
}

if (browserPrevBtn) browserPrevBtn.onclick = () => wsSend({ action: "navigate_verse", direction: -1, broadcast: false });
if (browserNextBtn) browserNextBtn.onclick = () => wsSend({ action: "navigate_verse", direction: 1, broadcast: false });

// ── Manual reference bar (Live Output) ───────────────────────────────
function goToReference() {
  const book = refBook.value.trim();
  wsSend({
    action: "lookup_reference",
    book,
    chapter: parseInt(refChapter.value, 10) || 1,
    verse: parseInt(refVerse.value, 10) || 1,
  });
}
if (refGoBtn) refGoBtn.onclick = goToReference;
[refBook, refChapter, refVerse].forEach(el => {
  if (el) el.addEventListener("keydown", e => { if (e.key === "Enter") goToReference(); });
});
if (navPrevBtn) navPrevBtn.onclick = () => wsSend({ action: "navigate_verse", direction: -1 });
if (navNextBtn) navNextBtn.onclick = () => wsSend({ action: "navigate_verse", direction: 1 });
if (stagePrevBtn) stagePrevBtn.onclick = () => wsSend({ action: "navigate_verse", direction: -1, broadcast: true });
if (stageNextBtn) stageNextBtn.onclick = () => wsSend({ action: "navigate_verse", direction: 1, broadcast: true });
if (broadcastBtn) broadcastBtn.onclick = () => broadcastFromPreview();

if (refDisplayBtn) refDisplayBtn.onclick = () => {
  const book = refBook.value.trim();
  wsSend({
    action: "lookup_reference",
    book,
    chapter: parseInt(refChapter.value, 10) || 1,
    verse: parseInt(refVerse.value, 10) || 1,
    broadcast: true,
  });
};

// ── Keyboard shortcuts (see COMMANDS.md) ─────────────────────────────
document.addEventListener("keydown", e => {
  const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName);
  if (e.key === "Enter") {
    if (typing) return;
    e.preventDefault();
    broadcastFromPreview();
    return;
  }
  if (e.ctrlKey && (e.key === "g" || e.key === "G")) { e.preventDefault(); refBook?.focus(); refBook?.select(); return; }
  if (e.key === "Escape" && !typing) { renderPreview(null); renderBrowserPreview(null); wsSend({ action: "clear_preview" }); return; }
  if (typing || e.ctrlKey || e.altKey || e.metaKey) return;
  
  // Prevent global ArrowUp/ArrowDown verse navigation if we are focusing or typing inside scrollable panel lists
  const isInsideScrollable = e.target.closest && (
    e.target.closest("#txScroll") || 
    e.target.closest("#searchResults") || 
    e.target.closest("#recallFeed") ||
    e.target.closest(".browser-list") ||
    e.target.closest(".chapter-grid") ||
    e.target.closest(".log-feed")
  );
  if (isInsideScrollable) return;

  if (e.key === "ArrowDown") { e.preventDefault(); wsSend({ action: "navigate_verse", direction: 1, broadcast: false }); }
  else if (e.key === "ArrowUp") { e.preventDefault(); wsSend({ action: "navigate_verse", direction: -1, broadcast: false }); }
});

// The sidebar is four entries; everything else lives behind a sub-tab.
// SUBVIEW_HOME maps the old view names (still used by deep links like the
// header error dot) onto their new home.
const SUBVIEW_HOME = {
  vmix: "settings", appearance: "settings", bible: "settings",
  mic: "settings", detection: "settings",
  logs: "more", developer: "more"
};

function showSubview(view, sub) {
  const host = $("view-" + view);
  if (!host || !sub) return;
  host.querySelectorAll(".subtab").forEach(t => t.classList.toggle("active", t.dataset.sub === sub));
  host.querySelectorAll(".subview").forEach(s => s.classList.toggle("active", s.id === "sub-" + sub));
}

function showView(name, sub) {
  const home = SUBVIEW_HOME[name];
  const viewName = home || name;
  if (home) sub = sub || name;
  document.querySelectorAll(".nav-item").forEach(n => n.classList.toggle("active", n.dataset.view === viewName));
  document.querySelectorAll(".view").forEach(v => v.classList.toggle("active", v.id === "view-" + viewName));
  if (sub) showSubview(viewName, sub);
  if (viewName === "scripture") ensureBibleStructure();
}
document.querySelectorAll(".nav-item").forEach(item => {
  item.onclick = () => showView(item.dataset.view);
});
document.querySelectorAll(".subtab").forEach(tab => {
  tab.onclick = () => showSubview(tab.closest(".view").id.replace("view-", ""), tab.dataset.sub);
});
if (gotoRecallBtn) gotoRecallBtn.onclick = () => {
  showView("live");
  setTimeout(() => liveBottomDock?.scrollIntoView({ behavior: "smooth", block: "nearest" }), 50);
};
if (headerLogDot) headerLogDot.onclick = () => showView("logs");
if (clearLogsBtn) clearLogsBtn.onclick = () => {
  if (logFeed) logFeed.innerHTML = "";
  logCount = 0;
  if (logBadge) logBadge.style.display = "none";
  headerLogDot?.classList.remove("show");
  navLogs?.classList.remove("has-errors");
};
if (copyLogsBtn) copyLogsBtn.onclick = () => {
  const lines = [...logFeed.querySelectorAll(".log-row")].map(r => r.dataset.plain || "").reverse();
  ndiEnabledToggle.onchange = () => wsSend({ action: "set_ndi_enabled", enabled: ndiEnabledToggle.checked });
}

// ── Tabs (legacy — hidden) ──
document.querySelectorAll(".tab").forEach(tab => {
  tab.onclick = () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    tab.classList.add("active");
    $("tab-" + tab.dataset.tab).classList.add("active");
  };
});

// ── WebSocket (with reconnect — the batch file opens the UI before the
//    backend may have finished loading the search index) ──
function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(connectWs, 2000);
}

function connectWs() {
  ws = new WebSocket("ws://localhost:8765");
  ws.onopen  = () => {
    backendReady = false;
    resetStartupBar();
    setStatus("connecting");
    structureRequested = false;
    voiceKeywordsRequested = false;
    ensureBibleStructure();
    syncVoiceNavOptions();
    wsSend({ action: "check_requirements" });
    wsSend({ action: "get_audio_devices" });
  };
  ws.onclose = () => { backendReady = false; setStatus("disconnected"); scheduleReconnect(); };
  ws.onerror = () => { backendReady = false; setStatus("error"); };
  ws.onmessage = onWsMessage;
}

function onWsMessage({ data }) {
  let msg;
  try { msg = JSON.parse(data); } catch { return; }
  switch (msg.type) {
    case "startup_progress":
      renderStartupStep(msg.step, msg.label, msg.status, msg.percent);
      break;
    case "status":
      if (msg.state === "ready") {
        backendReady = true;
        setStartupPercent(100);
      } else if (msg.state === "error") {
        backendReady = false;
        hideAppLoadingOverlay();
      }
      setStatus(msg.state);
      break;
    case "requirements_status":
      handleRequirementsStatus(msg);
      break;
    case "speech_started": lastSpeechActivityAt = Date.now(); showHearingIndicator(); break;
    case "transcript_live": 
      lastSpeechActivityAt = Date.now(); 
      updateInterim(msg.text); 
      if (typeof handleOnboardingTranscript === "function") handleOnboardingTranscript(msg.text, false);
      break;
    case "transcript_partial": 
      lastSpeechActivityAt = Date.now(); 
      appendTranscript(msg.text); 
      if (typeof handleOnboardingTranscript === "function") handleOnboardingTranscript(msg.text, true);
      break;
    case "detection":
      renderTranscriptDetection(msg);
      appendJson({
        book: msg.book, chapter: msg.chapter, verse: msg.verse,
        source: msg.source, confidence: msg.confidence,
        confidence_band: msg.confidence_band,
        latency_ms: msg.latency_ms, auto_display: msg.auto_display,
      });
      vmixDbDot.className = "dot ok";
      vmixDbTxt.textContent = `Bible DB: responding (${currentVersion || "—"})`;
      break;
    case "library":
      backendReady = true;
      // The Bible file changed (or finished loading) — book/chapter
      // structure has to come from the new one.
      structureRequested = false;
      ensureBibleStructure();
      renderLibrary(msg);
      if (sTxt.textContent === "connecting" || sTxt.textContent === "booting") {
        setStatus("ready");
      }
      break;
    case "broadcast_state":
      // Reflects state pushed by an external OSC controller (e.g. a
      // Pewbeam-compatible control surface hitting /pew/show, /pew/hide,
      // /pew/on_air) so the UI never silently disagrees with what's
      // actually on air.
      if (typeof msg.on_air === "boolean") {
        liveDot.classList.toggle("on", msg.on_air);
        liveTxt.textContent = msg.on_air ? "on air" : "standby";
connectWs();
setStatus("disconnected");

// ── Controls ──
hydrateIcons();
const iconObserver = new MutationObserver(muts => {
  for (const m of muts) {
    for (const node of m.addedNodes) {
      if (node.nodeType === 1) hydrateIcons(node);
    }
  }
});
iconObserver.observe(document.body, { childList: true, subtree: true });

micBtn.onclick  = () => { userPressedStart = true; wsSend({ action: "start_mic" }); };
stopBtn.onclick = () => wsSend({ action: "stop" });
if ($("refreshBgBtn")) {
  $("refreshBgBtn").onclick = () => {
    wsSend({ action: "refresh_backgrounds" });
  };
}
searchInput.addEventListener("keydown", e => {
  if (e.key === "Enter") {
    const q = searchInput.value.trim();
    if (q) {
      if (searchResults) {
        searchResults.innerHTML = '<div class="search-empty">Searching…</div>';
      }
      wsSend({
        action: "search_verse",
        query: q,
        testament: searchTestament?.value || searchTestamentFilter || "all",
      });
    }
  }
});

      if (ws && ws.readyState === WebSocket.OPEN) {
        wsSend({ action: "check_requirements" });
        wsSend({ action: "get_audio_devices" });
      }
    }
  }
}

// Wire up Buttons for Onboarding Step navigation
const nextBtn0 = $("btnOnboardingNext-0");
if (nextBtn0) nextBtn0.onclick = () => showOnboardingStep(1);

const skipBtn = $("btnOnboardingSkip");
if (skipBtn) skipBtn.onclick = () => showOnboardingStep(1);

const backBtn1 = $("btnOnboardingBack-1");
if (backBtn1) {
  backBtn1.onclick = () => {
    wsSend({ action: "stop" });
    const micStartBtn = $("btnOnboardingMicStart");
    const micStopBtn = $("btnOnboardingMicStop");
    if (micStartBtn) micStartBtn.disabled = false;
    if (micStopBtn) micStopBtn.disabled = true;
    showOnboardingStep(0);
  };
}

const nextBtn1 = $("btnOnboardingNext-1");
if (nextBtn1) {
  nextBtn1.onclick = () => {
    wsSend({ action: "stop" });
    const micStartBtn = $("btnOnboardingMicStart");
    const micStopBtn = $("btnOnboardingMicStop");
    if (micStartBtn) micStartBtn.disabled = false;
    if (micStopBtn) micStopBtn.disabled = true;
    showOnboardingStep(2);
  };
}

// Step 1 mic controls
const onboardMicStartBtn = $("btnOnboardingMicStart");
const onboardMicStopBtn = $("btnOnboardingMicStop");
const onboardMicSelect = $("onboardingMicSelect");

if (onboardMicSelect) {
  onboardMicSelect.onchange = () => {
    wsSend({ action: "set_mic", name: onboardMicSelect.value });
  };
}

if (onboardMicStartBtn) {
  onboardMicStartBtn.onclick = () => {
    wsSend({ action: "start_mic" });
    onboardMicStartBtn.disabled = true;
    if (onboardMicStopBtn) onboardMicStopBtn.disabled = false;
  };
}

if (onboardMicStopBtn) {
  onboardMicStopBtn.onclick = () => {
    wsSend({ action: "stop" });
    if (onboardMicStartBtn) onboardMicStartBtn.disabled = false;
    onboardMicStopBtn.disabled = true;
  };
}

// Step 2 Win+H controls
const voiceTypingArea = $("onboardingVoiceTypingArea");
const voiceTypingDot = $("voiceTypingDot");
const voiceTypingMsg = $("voiceTypingMsg");
const nextBtn2 = $("btnOnboardingNext-2");

if (voiceTypingArea) {
  voiceTypingArea.oninput = () => {
    const text = voiceTypingArea.value.trim();
    if (text.length > 0) {
      if (voiceTypingDot) {
        voiceTypingDot.style.background = "#2b9bff";
        voiceTypingDot.style.boxShadow = "0 0 0 3px rgba(43,155,255,0.2)";
      }
      if (voiceTypingMsg) {
        voiceTypingMsg.innerHTML = '<span style="color: #2b9bff; font-weight: 600;">✓ Input detected!</span> Windows Voice Typing verified.';
      }
      if (nextBtn2) nextBtn2.disabled = false;
    }
  };
}

const backBtn2 = $("btnOnboardingBack-2");
if (backBtn2) backBtn2.onclick = () => showOnboardingStep(1);

const nextBtn3 = $("btnOnboardingNext-3");
const backBtn3 = $("btnOnboardingBack-3");
if (backBtn3) backBtn3.onclick = () => showOnboardingStep(2);

const finishBtn = $("btnOnboardingFinish");
if (finishBtn) {
  finishBtn.onclick = () => {
    localStorage.setItem('onboarding_completed', 'true');
    const overlay = $("onboardingOverlay");
    if (overlay) overlay.classList.add("hidden");
    wsSend({ action: "stop" });
  };
}

// Settings "Re-run Onboarding" Button wire up
const launchOnboardingBtn = $("btnLaunchOnboarding");
if (launchOnboardingBtn) {
  launchOnboardingBtn.onclick = (e) => {
    e.preventDefault();
    const overlay = $("onboardingOverlay");
    if (overlay) {
      overlay.classList.remove("hidden");
      showOnboardingStep(0);
      wsSend({ action: "check_requirements" });
      wsSend({ action: "get_audio_devices" });
    }
  };
}

// Let's hook into window load to trigger onboarding check
window.addEventListener("load", () => {
  initOnboarding();
});