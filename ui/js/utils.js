const $ = id => document.getElementById(id);

const sDot=$("sDot"), sTxt=$("sTxt");
const micBtn=$("micBtn"), stopBtn=$("stopBtn");
const txFeed=$("txFeed"), txEmpty=$("txEmpty"), txFooter=$("txFooter"), txCount=$("txCount"), txScroll=$("txScroll");
const engineBody=$("engineBody"), engineEmpty=$("engineEmpty"), detCount=$("detCount");
function showToast(msg, { success = false, duration = 3200 } = {}) {
  if (!actionToast) return;
  actionToast.textContent = msg;
  actionToast.classList.remove("leaving");
  actionToast.classList.toggle("success", success);
  actionToast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    actionToast.classList.add("leaving");
    setTimeout(() => actionToast.classList.remove("show", "leaving"), 400);
  }, duration);
}

// ── Transcript ──
let hearingEl = null;
let interimEl = null;   // live-typing line, replaced/removed once the chunk finalizes

// "Stick to bottom" pattern: only auto-scroll to the newest line if the
// user was already at (or near) the bottom before this line arrived. If
// they've manually scrolled up to re-read something earlier, new lines
// keep arriving below without yanking their view back down -- they stay
// in control, and pressing the (added) "jump to latest" affordance isn't
// needed since scrolling back down to the edge re-engages sticking.
function isNearBottom() {
  return txScroll.scrollHeight - txScroll.scrollTop - txScroll.clientHeight < 40;
}
function scrollToLatest() {
  txScroll.scrollTop = txScroll.scrollHeight;
}
function tsLabel() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function showHearingIndicator() {
  if (hearingEl) return;
  const stick = isNearBottom();
  txEmpty.style.display = "none";
  hearingEl = document.createElement("div");
  hearingEl.className = "tx-line hearing";
  hearingEl.innerHTML = `<span class="tx-ts">${tsLabel()}</span><span class="tx-text">🎤 …</span>`;
  txFeed.appendChild(hearingEl);
  if (stick) scrollToLatest();
  setTimeout(() => { if (hearingEl) { hearingEl.remove(); hearingEl = null; } }, 5000);
}
function playLogChime() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    o.connect(g); g.connect(ctx.destination);
    o.frequency.value = 880; g.gain.value = 0.08;
    o.start(); o.stop(ctx.currentTime + 0.12);
  } catch (_) {}
}

function copyTextToClipboard(text, okMsg) {
  if (!text) { showToast("Nothing to copy"); return; }
  navigator.clipboard.writeText(text).then(
    () => showToast(okMsg || "Copied to clipboard"),
    () => showToast("Could not copy — check browser permissions")
  );
}

function appendSystemLog(msg) {
  if (!logFeed) return;
  logCount++;
  const level = msg.level || "warn";
  const ts = msg.ts || tsLabel();
  const body = `${ts} — ${msg.message || msg.code || "Event"}`;
  const fix = msg.fix ? `\nFix: ${msg.fix}` : "";
  const plain = body + fix;
  const row = document.createElement("div");
  row.className = "log-row " + level;
  row.dataset.plain = plain;
  const fixHtml = msg.fix ? `<div class="log-fix"><b>Fix:</b> ${msg.fix}</div>` : "";
  row.innerHTML = `<div class="log-row-body"><div><span style="opacity:.6">${ts}</span> — ${msg.message || msg.code || "Event"}</div>${fixHtml}</div><button type="button" class="log-copy-btn" title="Copy log entry">📋</button>`;
  row.querySelector(".log-copy-btn").onclick = (e) => {
    e.stopPropagation();
    copyTextToClipboard(row.dataset.plain, "Log entry copied");
  };
  logFeed.prepend(row);
  while (logFeed.childElementCount > 100) logFeed.removeChild(logFeed.lastChild);
  // The sidebar badge means "something needs your attention" — routine
  // info entries (a saved transcript) must never light it up red.
  if (level === "info") return;
  if (logBadge) { logBadge.style.display = ""; logBadge.textContent = String(logCount); }
  if (headerLogDot) headerLogDot.classList.add("show");
  if (navLogs) navLogs.classList.add("has-errors");
  if (level === "error") playLogChime();
}

function appendInfoLog(text) {
  appendSystemLog({ level: "info", message: text, ts: tsLabel() });
}
// Interim hypothesis text -- this is what makes the transcript feel like
// it's writing itself as the preacher speaks, instead of only updating in
// visible chunks every few seconds. Server sends "transcript_live" while a
// chunk is still being recognized; "transcript_partial" replaces it once
// that chunk is final. If the backend build in use doesn't send
// transcript_live yet, this simply never fires and appendTranscript alone
// still works exactly as before.
function updateInterim(text) {
  if (!text) return;
  if (hearingEl) { hearingEl.remove(); hearingEl = null; }
  txEmpty.style.display = "none";
  const stick = isNearBottom();
  if (!interimEl) {
    interimEl = document.createElement("div");
    interimEl.className = "tx-line interim";
    interimEl.innerHTML = `<span class="tx-ts">${tsLabel()}</span><span class="tx-text"></span>`;
    txFeed.appendChild(interimEl);
  }
  interimEl.querySelector(".tx-text").textContent = text;
  if (stick) scrollToLatest();
}
function appendTranscript(text) {
  if (!text) return;
  const stick = isNearBottom();
  if (hearingEl) { hearingEl.remove(); hearingEl = null; }
  if (interimEl) { interimEl.remove(); interimEl = null; }
  txEmpty.style.display = "none";
  // older lines fade from bright "fresh" to the dimmer resting color
  // (CSS transition on .tx-line handles the actual fade)
  txFeed.querySelectorAll(".tx-line.fresh").forEach(el => el.classList.remove("fresh"));
  const div = document.createElement("div");
  div.className = "tx-line fresh";
  div.innerHTML = `<span class="tx-ts">${tsLabel()}</span><span class="tx-text"></span>`;
  div.querySelector(".tx-text").textContent = text;
  txFeed.appendChild(div);
  txLines++;
  txCount.textContent = `${txLines} line${txLines !== 1 ? "s" : ""}`;
  // Oldest line is now the FIRST child (chronological top-to-bottom order),
  // so trim from the top, not the bottom, once past the cap.
  while (txFeed.childElementCount > 80) txFeed.removeChild(txFeed.firstChild);
  if (stick) scrollToLatest();

  sessionLines.push({ ts: new Date().toLocaleTimeString(), text });
}

// ── Save Transcript ──
// The backend already appends every chunk to logs/transcript_<date>.log as
// it happens (see server.py _append_transcript_log) -- that's the
// crash-proof copy. This button is the operator-facing convenience: a
// clean, timestamped .txt of exactly this session, downloaded on demand,
// no extra click-through to the filesystem needed mid-service.
function saveTranscript() {
  if (sessionLines.length === 0) {
    appendInfoLog("Nothing transcribed yet this session — nothing to save.");
    return;
  }
  const header = `WindowVerse transcript — session started ${sessionLines[0].ts}, saved ${new Date().toLocaleString()}\n${"=".repeat(60)}\n\n`;
  const body = sessionLines.map(l => `[${l.ts}] ${l.text}`).join("\n");
  const blob = new Blob([header + body], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  a.href = url;
  a.download = `WindowVerse_Transcript_${stamp}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
saveBtn.onclick = saveTranscript;

// ── Detection / Engine panel ──
// Suggestions is a transcript-only column: the ONLY thing that puts a card
// here is speech detection. Search, the Scripture Browser and manual
// navigation all go to Preview instead, so a lookup mid-sermon never
// pollutes the record of what was actually preached.
function renderTranscriptDetection(d) {
  dets++;
  detCount.textContent = `${dets} detection${dets !== 1 ? "s" : ""}`;
  engineEmpty.style.display = "none";
  const band = d.confidence_band || "medium";
  const pct  = Math.round((d.confidence || 0) * 100);
  const card = document.createElement("div");
  card.className = "verse-card";
  card.innerHTML = `
    <div class="verse-source"><span>${iconSvg("spark", 11)}</span>${(d.source||"detection").toUpperCase()}</div>
    <div class="verse-ref">${d.book} ${d.chapter}:${d.verse}</div>
    <div class="verse-text">${d.text}</div>
    <div class="verse-meta">
      <span class="conf-pill conf-${band}">${pct}%</span>
      <span>${band} confidence</span>
      ${d.latency_ms ? `<span class="meta-sep">·</span><span>${Math.round(d.latency_ms)}ms</span>` : ""}
      <span class="meta-sep">·</span><span>NKJV</span>
    </div>`;
  card.onclick = () => displayToPreview(d);
  engineBody.prepend(card);
  while (engineBody.childElementCount > 25) engineBody.removeChild(engineBody.lastChild);
  addToRecall(d);
}

  if (!verse) { showToast("Nothing in preview to broadcast"); return; }
      showToast("Pop-up blocked. Enable pop-ups or use the desktop app.");
    }
  }
}
if (popoutBtn) popoutBtn.onclick = openProjector;
if (vmixOpenBtn) vmixOpenBtn.onclick = openProjector;

const stageScroll = stage.parentElement;
if (stageScroll && typeof ResizeObserver !== "undefined") {
  let stageResizeTimer = null;
  let lastObservedWidth = 0;
  let lastObservedHeight = 0;
  new ResizeObserver(entries => {
    for (let entry of entries) {
      const w = Math.round(entry.contentRect.width);
      const h = Math.round(entry.contentRect.height);
      if (Math.abs(w - lastObservedWidth) > 4 || Math.abs(h - lastObservedHeight) > 4) {
        lastObservedWidth = w;
        lastObservedHeight = h;
        if (!lastStageVerse) return;
        clearTimeout(stageResizeTimer);
        stageResizeTimer = setTimeout(() => sendToStage(lastStageVerse), 80);
      }
    }
  }).observe(stageScroll);
}

// Poll status — in the desktop app we assume it stays open once launched.
setInterval(() => {
  if (projectorNative) {
    vmixWinDot.className = "dot on";
    vmixWinTxt.textContent = "Projector window: active";
  } else {
    vmixWinDot.className = "dot";
    vmixWinTxt.textContent = "Projector window: closed";
  }
}, 2000);

// ── Quick Recall ──
// Grouped by book so the list can't saturate: each book shows only its most
// recent verse, with a caret that reveals the older ones underneath.
const recallGroups = [];   // [{ book, verses: [newest, …] }] — newest book first
const recallOpen = new Set();

function addToRecall(d) {
  if (!d || !d.book) return;
  recallEmpty.style.display = "none";
  let group = recallGroups.find(g => g.book === d.book);
  if (group) {
    recallGroups.splice(recallGroups.indexOf(group), 1);
    group.verses = group.verses.filter(
      v => !(v.chapter === d.chapter && v.verse === d.verse));
  } else {
    group = { book: d.book, verses: [] };
  }
  group.verses.unshift(d);
  group.verses = group.verses.slice(0, 20);
  recallGroups.unshift(group);
  while (recallGroups.length > 15) recallGroups.pop();
  renderRecall();
}

function renderRecall() {
  recallFeed.innerHTML = "";
  for (const group of recallGroups) {
    const [latest, ...older] = group.verses;
    const wrap = document.createElement("div");
    wrap.className = "recall-group" + (recallOpen.has(group.book) ? " open" : "");

    const head = document.createElement("div");
    head.className = "recall-item";
    const caret = document.createElement("span");
    caret.className = "recall-caret" + (older.length ? "" : " placeholder");
    caret.innerHTML = iconSvg(recallOpen.has(group.book) ? "down" : "next", 13);
    caret.onclick = e => {
      e.stopPropagation();
      if (!older.length) return;
      recallOpen.has(group.book) ? recallOpen.delete(group.book) : recallOpen.add(group.book);
      renderRecall();
    };
    const label = document.createElement("span");
    label.className = "recall-ref";
    label.textContent = `${latest.book} ${latest.chapter}:${latest.verse}`;
    const snip = document.createElement("span");
    snip.className = "recall-snip";
    snip.textContent = latest.text || "";
    head.append(caret, label, snip);
    if (older.length) {
      const count = document.createElement("span");
      count.className = "recall-count";
      count.textContent = `+${older.length}`;
      head.appendChild(count);
    }
    head.onclick = () => displayToPreview(latest);
    wrap.appendChild(head);

    const children = document.createElement("div");
    children.className = "recall-children";
    for (const v of older) {
      const row = document.createElement("div");
      row.className = "recall-item";
      const ref = document.createElement("span");
      ref.className = "recall-ref";
      ref.textContent = `${v.book} ${v.chapter}:${v.verse}`;
      const text = document.createElement("span");
      text.className = "recall-snip";
      text.textContent = v.text || "";
      row.append(ref, text);
      row.onclick = () => displayToPreview(v);
      children.appendChild(row);
    }
    wrap.appendChild(children);
    recallFeed.appendChild(wrap);
  }
}

// ── Voice keyword editor ──
// The stock phrases can be switched off one by one ("continue" and "back"
// are the usual suspects) and the operator's own wording added per intent.
const VOICE_INTENT_LABELS = {
  next: "Next verse", prev: "Previous verse", repeat: "Repeat",
  clear: "Clear screen", broadcast: "Display",
};

  if (!text) { showToast("No JSON log entries to copy"); return; }
  navigator.clipboard.writeText(text).then(
    () => showToast("JSON log copied to clipboard"),
    () => showToast("Could not copy — check browser permissions")
  );
}
if (copyJsonBtn) copyJsonBtn.onclick = copyJsonLog;

// ── Bible version / language library ──
  showToast("Not connected to backend — reconnecting…");
  return false;
}

function onSecondaryOrderChange() {
  const above = secondaryAbove && secondaryAbove.checked;
  if (above === secondaryAbovePrimary) return;
  secondaryAbovePrimary = above;
  if (!book) { showToast("Type a book name first"); return; }
  if (!book) { showToast("Type a book name first"); return; }
  copyTextToClipboard(lines.join("\n\n"), "All logs copied");
};

function applyColumnOrder(order) {
  if (!mainGrid || !order?.length) return;
  const cols = {};
  mainGrid.querySelectorAll(".col[data-col]").forEach(c => { cols[c.dataset.col] = c; });
  order.forEach(id => { if (cols[id]) mainGrid.appendChild(cols[id]); });
}
function initColumnDrag() {
  if (!mainGrid) return;
  let saved;
  try { saved = JSON.parse(localStorage.getItem(COL_ORDER_KEY) || "null"); } catch { saved = null; }
  applyColumnOrder(saved || ["tx", "suggest", "stage"]);
  let dragEl = null;
  mainGrid.querySelectorAll(".col[data-col]").forEach(col => {
    col.addEventListener("dragstart", e => {
      dragEl = col;
      col.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });
    col.addEventListener("dragend", () => {
      col.classList.remove("dragging");
      dragEl = null;
      const order = [...mainGrid.querySelectorAll(".col[data-col]")].map(c => c.dataset.col);
      localStorage.setItem(COL_ORDER_KEY, JSON.stringify(order));
    });
    col.addEventListener("dragover", e => {
      e.preventDefault();
      if (!dragEl || dragEl === col) return;
      const rect = col.getBoundingClientRect();
      const after = e.clientX > rect.left + rect.width / 2;
      mainGrid.insertBefore(dragEl, after ? col.nextSibling : col);
    });
  });
}

// A search may grow the dock past this, but never below what the operator
// last dragged it to.
const DOCK_MIN_HEIGHT = 190;
function dockBaseHeight() {
  return Math.max(DOCK_MIN_HEIGHT, parseInt(localStorage.getItem(DOCK_HEIGHT_KEY) || "0", 10) || 0);
}

function initLayoutResize() {
  const dock = $("liveBottomDock");
  const dockResizer = $("dockResizer");
  const sidebarResizer = $("sidebarResizer");
  const browserGrid = $("browserGrid");

  try {
    const savedWidths = JSON.parse(localStorage.getItem(COL_WIDTHS_KEY) || "null");
    if (savedWidths && mainGrid) {
      mainGrid.querySelectorAll(".col").forEach((col, i) => {
        if (savedWidths[i]) col.style.flex = `0 0 ${savedWidths[i]}px`;
      });
    }
    const savedBrowserWidths = JSON.parse(localStorage.getItem(BROWSER_COL_WIDTHS_KEY) || "null");
    if (savedBrowserWidths && browserGrid) {
      browserGrid.querySelectorAll(".browser-col").forEach((col, i) => {
        if (savedBrowserWidths[i]) col.style.flex = `0 0 ${savedBrowserWidths[i]}px`;
      });
    }
  } catch { /* ignore */ }

  mainGrid?.querySelectorAll(".col-resize-handle").forEach(handle => {
    handle.addEventListener("mousedown", e => {
      e.preventDefault();
      const col = handle.closest(".col");
      if (!col) return;
      const startX = e.clientX;
      const startW = col.getBoundingClientRect().width;
      handle.classList.add("active");
      const onMove = ev => {
        const w = Math.max(160, startW + ev.clientX - startX);
        col.style.flex = `0 0 ${w}px`;
      };
      const onUp = () => {
        handle.classList.remove("active");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        const widths = [...mainGrid.querySelectorAll(".col")].map(c => Math.round(c.getBoundingClientRect().width));
        localStorage.setItem(COL_WIDTHS_KEY, JSON.stringify(widths));
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  });

  browserGrid?.querySelectorAll(".col-resize-handle").forEach(handle => {
    handle.addEventListener("mousedown", e => {
      e.preventDefault();
      const col = handle.closest(".browser-col");
      if (!col) return;
      const startX = e.clientX;
      const startW = col.getBoundingClientRect().width;
      handle.classList.add("active");
      const onMove = ev => {
        const w = Math.max(100, startW + ev.clientX - startX);
        col.style.flex = `0 0 ${w}px`;
      };
      const onUp = () => {
        handle.classList.remove("active");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        const widths = [...browserGrid.querySelectorAll(".browser-col")].map(c => Math.round(c.getBoundingClientRect().width));
        localStorage.setItem(BROWSER_COL_WIDTHS_KEY, JSON.stringify(widths));
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  });

  if (dock && dockResizer) {
    const savedH = localStorage.getItem(DOCK_HEIGHT_KEY);
    if (savedH) dock.style.height = savedH + "px";
    dockResizer.addEventListener("mousedown", e => {
      e.preventDefault();
      const startY = e.clientY;
      const startH = dock.getBoundingClientRect().height;
      dockResizer.classList.add("active");
      const onMove = ev => {
        const h = Math.max(120, Math.min(window.innerHeight * 0.5, startH - (ev.clientY - startY)));
        dock.style.height = h + "px";
      };
      const onUp = () => {
        dockResizer.classList.remove("active");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        localStorage.setItem(DOCK_HEIGHT_KEY, String(Math.round(dock.getBoundingClientRect().height)));
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }

  if (sidebar && sidebarResizer) {
    const savedSw = parseInt(localStorage.getItem(SIDEBAR_WIDTH_KEY) || "56", 10);
    if (savedSw > 70) {
      sidebar.style.width = savedSw + "px";
      sidebar.classList.add("sidebar-wide");
    }
    sidebarResizer.addEventListener("mousedown", e => {
      e.preventDefault();
      const startX = e.clientX;
      const startW = sidebar.getBoundingClientRect().width;
      sidebarResizer.classList.add("active");
      const onMove = ev => {
        const w = Math.max(56, Math.min(320, startW + ev.clientX - startX));
        sidebar.style.width = w + "px";
        sidebar.classList.toggle("sidebar-wide", w > 80);
      };
      const onUp = () => {
        sidebarResizer.classList.remove("active");
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        localStorage.setItem(SIDEBAR_WIDTH_KEY, String(Math.round(sidebar.getBoundingClientRect().width)));
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }
}

function renderNdiState(msg) {
  ndiEnabled = msg.enabled !== false;
  const toggle = $("ndiEnabledToggle");
  if (toggle) toggle.checked = ndiEnabled;
  const avail = !!msg.available;
  const dot = $("ndiAvailDot"), txt = $("ndiAvailTxt");
  if (dot) dot.className = "dot" + (avail ? " ok" : " bad");
  if (txt) txt.textContent = avail ? "NDI runtime: available" : "NDI runtime: not installed";
  const bDot = $("ndiBroadcastDot"), bTxt = $("ndiBroadcastTxt");
  if (bDot) bDot.className = "dot" + (msg.broadcasting && ndiEnabled ? " ok" : "");
  if (bTxt) {
    bTxt.textContent = !ndiEnabled ? "Broadcast: disabled"
      : msg.broadcasting ? "Broadcast: live on NDI" : "Broadcast: standby";
  }
}

        showToast(
          auto ? `Transcript saved after ${secs}s of silence` : "Transcript saved",
          { success: true, duration: 6000 },
        );
      }
      if (msg.code === "matched_reference_missing_from_db") {
        vmixDbDot.className = "dot bad";
        vmixDbTxt.textContent = "Bible DB: missing row for last reference";
      } else if (msg.code === "startup_self_check_failed") {
        vmixDbDot.className = "dot bad";
        vmixDbTxt.textContent = "Bible DB: startup check failed";
      } else if (msg.code === "mic_start_failed") {
        backendReady = true;
        setStatus("ready");
      }
      break;
    case "ndi_state":
      renderNdiState(msg);
      break;
    case "search_results":
      renderSearchResults(msg);
      break;
    case "search_result":
    case "manual_search_result":
      // Manual lookups stage only — the server sends preview_verse for the
      // actual verse, this branch just logs it.
      if (msg.result) appendJson(msg.result);
      else showToast("No confident match found for that phrase");
      break;
    case "preview_verse":
      displayToPreview(msg, { notifyServer: false });
      break;
    case "broadcast_verse":
      markOnAir(msg);
      addToRecall(msg);
      break;
    case "preview_cleared":
      showToast(`Voice: ${msg.intent}`);
      break;
    case "bible_structure":
      applyBibleStructure(msg);
      break;
    case "chapter_verses":
      applyChapterVerses(msg);
      break;
    case "browser_results":
      applyBrowserResults(msg);
      break;
    case "display_state":