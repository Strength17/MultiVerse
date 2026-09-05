let selectedMic = "";
let startupStepStatus = {};
const COL_ORDER_KEY = "wvColOrder";
const browserPreview = null;
const COL_WIDTHS_KEY = "wvColWidths";
const DOCK_HEIGHT_KEY = "wvDockHeight";
const SIDEBAR_WIDTH_KEY = "wvSidebarWidth";

// ── Status ──
function updateMicEmpty(state) {
  const ring = micRing();
  const text = micEmptyText();
  if (!ring || !text) return;
  ring.classList.remove("active", "starting");
  if (state === "listening" && txLines === 0) {
    txEmpty.style.display = "flex";
    ring.classList.add("active");
    text.innerHTML = "Microphone is live<br>Speak — words appear here as you talk";
  } else if (state === "starting") {
    txEmpty.style.display = "flex";
    ring.classList.add("starting");
    text.innerHTML = "Opening microphone…";
  } else if (txLines === 0) {
    txEmpty.style.display = "flex";
    const canStart = backendReady && (state === "ready" || state === "stopped");
    text.innerHTML = canStart
      ? "Ready — click Start to open the microphone"
      : state === "booting" || state === "connecting"
        ? "Waiting for backend to finish loading…"
        : "No transcription yet<br>Click Start to begin";
  }
}

function setStatus(state) {
  sTxt.textContent = state;
  const isLive = state === "listening";
  const isErr  = state === "disconnected" || state === "error";
  const canStart = backendReady && (state === "ready" || state === "stopped");
  sDot.className = "dot" + (isLive ? " live" : isErr ? " error" : state === "starting" ? " live" : "");
  micBtn.disabled  = !canStart || state === "starting" || isLive;
  stopBtn.disabled = !isLive;
  if (micProgress) {
    const showProg = state === "starting";
    micProgress.classList.toggle("show", showProg);
    if (!showProg && micProgressBar) micProgressBar.style.width = "0%";
  }
  txFooter.textContent = isLive
    ? "● Microphone live — speak now (saved to logs/transcript_*.log)"
    : state === "starting"
      ? "Opening microphone…"
    : canStart
      ? "Ready — press Start to open the microphone"
      : state === "booting" || state === "connecting"
        ? "Waiting for backend to finish loading…"
        : "Idle — press Start";

  if (micStatusPill) {
    micStatusPill.classList.toggle("show", isLive || state === "starting");
    micStatusPill.textContent = state === "starting" ? "● Opening mic…" : "● Mic live";
  }

  updateMicEmpty(state);

  // vMix tab + connection banner mirror the same signal, red when it fails
  vmixWsDot.className = "dot" + (isLive ? " ok" : isErr ? " bad" : backendReady ? " ok" : "");
  vmixWsTxt.textContent = "Backend: " + state;
  if (isErr && everConnected) {
    connBanner.classList.add("show");
  } else {
    connBanner.classList.remove("show");
  }
  if (!isErr && state !== "connecting") everConnected = true;

  if (isLive) {
    startVMMeter();
  } else {
    stopVMMeter();
  }

  if (backendReady || state === "ready") {
    const overlay = $("appLoadingOverlay");
    if (overlay) {
      setTimeout(() => {
        overlay.style.opacity = "0";
        overlay.style.pointerEvents = "none";
        setTimeout(() => {
          overlay.style.display = "none";
        }, 800);
      }, 300);
    }
  }

  updateStartupBarVisibility(state);
}

function updateStartupBarVisibility(state) {
  const show = !backendReady && state !== "disconnected" && state !== "error";
  startupBar.classList.toggle("show", show);
  if (backendReady) {
    startupTitle.textContent = "Backend ready";
  } else if (state === "connecting") {
    startupTitle.textContent = "Connecting to backend…";
  } else {
    startupTitle.textContent = "Loading backend…";
  }
}

function setStartupPercent(pct) {
  const n = Math.max(0, Math.min(100, Math.round(pct || 0)));
  if (startupProgressBar) startupProgressBar.style.width = n + "%";
  if (startupPct) startupPct.textContent = n + "%";

  const loadingProgressFill = $("loadingProgressFill");
  if (loadingProgressFill) loadingProgressFill.style.width = n + "%";

  const loadingOverlayPct = $("loadingOverlayPct");
  if (loadingOverlayPct) loadingOverlayPct.textContent = n + "%";
}

function floatStartupMessage(label) {
  if (!startupMsgStage || !label) return;
  const el = document.createElement("div");
  el.className = "startup-msg-float";
  el.textContent = label;
  startupMsgStage.appendChild(el);
  el.addEventListener("animationend", () => el.remove());
}

function resetStartupBar() {
  startupStepStatus = {};
  if (startupMsgStage) startupMsgStage.innerHTML = "";
  if (startupCurrentMsg) startupCurrentMsg.textContent = "";
  setStartupPercent(0);
}

function renderStartupStep(step, label, status, percent) {
  if (typeof percent === "number") setStartupPercent(percent);
  const prev = startupStepStatus[step];
  startupStepStatus[step] = status;

  if (status === "running") {
    if (startupCurrentMsg) startupCurrentMsg.textContent = label;
    const loadingStatusMsg = $("loadingStatusMsg");
    if (loadingStatusMsg) loadingStatusMsg.textContent = label;
    return;
  }
  if (status === "done" || status === "error") {
    if (startupCurrentMsg) startupCurrentMsg.textContent = "";
    floatStartupMessage(label);
    const loadingStatusMsg = $("loadingStatusMsg");
    if (loadingStatusMsg) loadingStatusMsg.textContent = label;
    return;
  }
  if (prev === "running" && startupCurrentMsg?.textContent) {
    floatStartupMessage(startupCurrentMsg.textContent);
    startupCurrentMsg.textContent = "";
  }
}

function renderVoiceKeywords(msg) {
  const host = $("voiceKeywords");
  if (!host) return;
  host.innerHTML = "";
  for (const group of msg.intents || []) {
    const block = document.createElement("div");
    block.className = "kw-intent";
    const name = document.createElement("div");
    name.className = "kw-intent-name";
    name.textContent = VOICE_INTENT_LABELS[group.intent] || group.intent;
    block.appendChild(name);

    const chips = document.createElement("div");
    chips.className = "kw-chips";
    for (const entry of group.builtin || []) {
      const chip = document.createElement("span");
      chip.className = "kw-chip" + (entry.enabled ? " on" : "");
      chip.innerHTML = iconSvg(entry.enabled ? "check" : "x", 12) + " " + entry.phrase;
      chip.title = entry.enabled ? "Click to switch off" : "Click to switch on";
function renderAudioDevices(msg) {
  const devices = msg.devices || msg;
  const selected = msg.selected || selectedMic || "";
  // "active" is the endpoint speech recognition actually opens, which is not
  // the same string as the selection when the selection is "System Default".
  const active = msg.active
    || (devices || []).find(d => d.name === selected)?.name
    || (devices || []).find(d => d.is_default)?.name
    || "";
  const micActive = $("micActive");
  if (micActive) {
    micActive.innerHTML = active
      ? `<b>Detected microphone</b>${escapeHtml(active)}`
      : `<b>Microphone</b>No input device detected`;
  }
  if (micSelect) {
    micSelect.innerHTML = (devices || []).map(d =>
      `<option value="${d.name}" ${d.name === selected ? "selected" : ""}>${d.name}</option>`
    ).join("");
    if (selected) micSelect.value = selected;
  }
  if (!micDeviceList) return;
  if (!devices?.length) {
    micDeviceList.innerHTML = `<div style="color:var(--ink-40);font-size:12px">No microphone devices found</div>`;
    return;
  }
  micDeviceList.innerHTML = devices.map(d => {
    const isActive = d.name === active;
    const tags = [
      isActive ? '<span class="mic-device-tag">In use</span>' : "",
      d.is_default ? '<span class="mic-device-tag">Default</span>' : "",
    ].filter(Boolean).join(" ");
    return `<div class="mic-device-row${isActive ? " active" : ""}" data-mic="${d.name.replace(/"/g, "&quot;")}">
      <span>${d.name}</span>${tags ? `<span style="margin-left:auto;display:flex;gap:4px">${tags}</span>` : ""}
    </div>`;
  }).join("");
  micDeviceList.querySelectorAll(".mic-device-row").forEach(row => {
    row.onclick = () => {
      selectedMic = row.dataset.mic;
      renderAudioDevices({ devices, selected: selectedMic, active: selectedMic });
    };
  });
}

// ── Sidebar navigation + panel mount ──
function mountSidePanels() {
  const vmixInner = document.querySelector("#tab-vmix .vmix-panel");
  if (vmixInner && $("panel-vmix")) $("panel-vmix").append(...vmixInner.childNodes);

  const settingsPanel = document.querySelector("#tab-settings .vmix-panel");
  if (settingsPanel) {
    const steps = [...settingsPanel.children];
    const appearance = $("panel-appearance");
    const micPanel = $("panel-mic"), dev = $("panel-developer");
    if (micPanel) {
      const wrap = document.createElement("div");
      wrap.className = "vmix-panel";
      const micStep = settingsPanel.querySelector("#micDeviceList")?.closest(".vmix-steps");
      if (micStep) wrap.appendChild(micStep);
      micPanel.appendChild(wrap);
    }
    if (appearance) {
      const wrap = document.createElement("div");
      wrap.className = "vmix-panel";
      const appSection = settingsPanel.querySelector("#dispAppearanceSection");
      if (appSection) wrap.appendChild(appSection);
      // Secondary-language position is a display choice, so it lives with the
      // rest of the verse appearance controls now that the Bible tab is gone.
      const orderRow = settingsPanel.querySelector("#secondaryOrderRow");
      if (orderRow) wrap.appendChild(orderRow);
      appearance.appendChild(wrap);
    }
    if (dev) {
      const wrap = document.createElement("div");
      wrap.className = "vmix-panel";
      settingsPanel.querySelectorAll("details.settings-advanced").forEach(el => {
        if (el.querySelector("#showJsonToggle")) wrap.appendChild(el);
      });
      dev.appendChild(wrap);
    }
    // Story narration + search/transcript tuning belong with the other
    // detection controls, otherwise they'd stay orphaned in the legacy tab.
    const detection = $("sub-detection")?.querySelector(".vmix-panel");
    if (detection) {
      settingsPanel.querySelectorAll("details.settings-advanced").forEach(el => {
        if (el.querySelector("#narrativeSensitivity") || el.querySelector("#settingsSearchTestament")) {
          detection.appendChild(el);
        }
      });
    }
  }
  
  // Enable scrolling with arrow keys in settings
  const sideScroll = document.querySelector(".side-scroll");
  if (sideScroll) {
    sideScroll.tabIndex = 0;
    sideScroll.addEventListener("keydown", (e) => {
      if (e.key === "ArrowUp") {
        sideScroll.scrollTop -= 50;
      } else if (e.key === "ArrowDown") {
        sideScroll.scrollTop += 50;
      }
    });
  }
}

// Ensure the microphone device list is updated immediately when the app starts
window.addEventListener('load', () => {
mountSidePanels();
      renderAudioDevices(msg);
      break;
  }
}