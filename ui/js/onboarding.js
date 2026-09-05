// ── Onboarding & Setup Wizard Controller ──
let currentOnboardingStep = 0;
const totalOnboardingSteps = 4;
let verifiedOnboardingTranscription = false;

function showOnboardingStep(stepIdx) {
  for (let i = 0; i < totalOnboardingSteps; i++) {
    const stepEl = $("onboardingStep-" + i);
    const ind = $("indStep-" + i);
    if (stepEl) {
      stepEl.classList.toggle("active", i === stepIdx);
    }
    if (ind) {
      ind.classList.toggle("active", i === stepIdx);
    }
  }
  currentOnboardingStep = stepIdx;
  
  // Update progress fill and percentage text
  const pct = 25 + stepIdx * 25;
  const progressFill = $("onboardingProgressFill");
  const pctText = $("onboardingPctText");
  if (progressFill) progressFill.style.width = pct + "%";
  if (pctText) pctText.textContent = pct + "%";
}

function hideAppLoadingOverlay() {
  const overlay = $("appLoadingOverlay");
  if (overlay) {
    overlay.style.opacity = "0";
    overlay.style.pointerEvents = "none";
    setTimeout(() => {
      overlay.style.display = "none";
    }, 800);
  }
}

function handleRequirementsStatus(msg) {
  // Update OS Check
  const osDot = $("req-os-dot");
  const osTitle = $("req-os-title");
  const osBadge = $("req-os-badge");
  const osRow = $("req-os-row");
  if (osDot && osTitle && osBadge) {
    if (msg.os_ok) {
      osDot.style.background = "#2b9bff";
      osTitle.textContent = msg.os_name || "Windows 10/11";
      osBadge.textContent = "Passed";
      osBadge.style.color = "#2b9bff";
      if (osRow) osRow.style.borderColor = "rgba(43,155,255,0.2)";
    } else {
      osDot.style.background = "#e05a4e";
      osTitle.textContent = msg.os_name || "Unsupported OS";
      osBadge.textContent = "Failed";
      osBadge.style.color = "#e05a4e";
      if (osRow) osRow.style.borderColor = "rgba(224,90,78,0.2)";
    }
  }

  // Update WinRT speech packages Check
  const winrtDot = $("req-winrt-dot");
  const winrtTitle = $("req-winrt-title");
  const winrtBadge = $("req-winrt-badge");
  const winrtRow = $("req-winrt-row");
  if (winrtDot && winrtTitle && winrtBadge) {
    if (msg.winrt_ok) {
      winrtDot.style.background = "#2b9bff";
      winrtTitle.textContent = "Speech engine loaded";
      winrtBadge.textContent = "Passed";
      winrtBadge.style.color = "#2b9bff";
      if (winrtRow) winrtRow.style.borderColor = "rgba(43,155,255,0.2)";
    } else {
      winrtDot.style.background = "#e05a4e";
      winrtTitle.textContent = "Missing speech packages";
      winrtBadge.textContent = "Failed";
      winrtBadge.style.color = "#e05a4e";
      if (winrtRow) winrtRow.style.borderColor = "rgba(224,90,78,0.2)";
    }
  }

  // Update Microphone Check
  const micDot = $("req-mic-dot");
  const micTitle = $("req-mic-title");
  const micBadge = $("req-mic-badge");
  const micRow = $("req-mic-row");
  if (micDot && micTitle && micBadge) {
    if (msg.mic_ok) {
      micDot.style.background = "#2b9bff";
      micTitle.textContent = `Microphone detected`;
      micBadge.textContent = "Passed";
      micBadge.style.color = "#2b9bff";
      if (micRow) micRow.style.borderColor = "rgba(43,155,255,0.2)";
    } else {
      micDot.style.background = "#e05a4e";
      micTitle.textContent = "No microphone found";
      micBadge.textContent = "Failed";
      micBadge.style.color = "#e05a4e";
      if (micRow) micRow.style.borderColor = "rgba(224,90,78,0.2)";
    }
  }

  // Update Bible DB Check
  const dbDot = $("req-db-dot");
  const dbTitle = $("req-db-title");
  const dbBadge = $("req-db-badge");
  const dbRow = $("req-db-row");
  if (dbDot && dbTitle && dbBadge) {
    if (msg.db_ok) {
      dbDot.style.background = "#2b9bff";
      dbTitle.textContent = "Bible database verified";
      dbBadge.textContent = "Passed";
      dbBadge.style.color = "#2b9bff";
      if (dbRow) dbRow.style.borderColor = "rgba(43,155,255,0.2)";
    } else {
      dbDot.style.background = "#e05a4e";
      dbTitle.textContent = "Bible DB missing";
      dbBadge.textContent = "Failed";
      dbBadge.style.color = "#e05a4e";
      if (dbRow) dbRow.style.borderColor = "rgba(224,90,78,0.2)";
    }
  }

  // Populate mic pickers inside onboarding with returned devices
  if (msg.mic_devices) {
    const onboardSelect = $("onboardingMicSelect");
    if (onboardSelect) {
      const currentVal = onboardSelect.value;
      onboardSelect.innerHTML = "";
      msg.mic_devices.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d.name;
        opt.textContent = d.name + (d.is_default ? " (Default)" : "");
        if (d.name === currentVal || (d.is_default && !currentVal)) {
          opt.selected = true;
        }
        onboardSelect.appendChild(opt);
      });
    }
  }

  // Display fix hint if any check failed
  const hintBox = $("onboardingFixHint");
  const nextBtn0 = $("btnOnboardingNext-0");
  if (hintBox) {
    let html = "";
    if (!msg.os_ok) {
      html += `<b>• Unsupported Windows Version:</b> Windows 10/11 is required to support Windows on-device speech API.<br>`;
    }
    if (!msg.winrt_ok) {
      html += `<b>• Missing Speech Packages:</b> WinRT python modules are missing. Please run:<br><code style="background:var(--bg);padding:2px 4px;font-family:var(--mono);font-size:11px;display:block;margin:4px 0;">pip install -r requirements_winrt.txt --break-system-packages</code>then restart WindowVerse.<br>`;
    }
    if (!msg.mic_ok) {
      html += `<b>• No Microphone Found:</b> Connect a working USB or analog mic. Confirm desktop microphone access is enabled under Windows Privacy settings.<br>`;
    }
    if (!msg.db_ok) {
      html += `<b>• Missing Bible DB:</b> Place your <code style="font-family:var(--mono);">NKJV.sqlite3</code> file under <code style="font-family:var(--mono);">Documents\\WindowVerse\\data\\NKJV\\English\\</code>.<br>`;
    }

    if (html) {
      hintBox.innerHTML = html;
      hintBox.style.display = "block";
    } else {
      hintBox.style.display = "none";
    }
  }

  // Enable Next button if everything passes
  const allPassed = msg.os_ok && msg.winrt_ok && msg.mic_ok && msg.db_ok;
  if (nextBtn0) {
    nextBtn0.disabled = !allPassed;
  }
}

function handleOnboardingTranscript(text, isFinal) {
  const box = $("onboardingTranscriptBox");
  if (!box) return;
  const placeholder = $("onboardingTranscriptPlaceholder");
  if (placeholder) placeholder.remove();

  if (isFinal) {
    const p = document.createElement("p");
    p.style.marginBottom = "4px";
    p.textContent = text;
    const testLiveSpan = $("onboardingTestLiveSpan");
    if (testLiveSpan) testLiveSpan.textContent = "";
    box.appendChild(p);
  } else {
    let testLiveSpan = $("onboardingTestLiveSpan");
    if (!testLiveSpan) {
      testLiveSpan = document.createElement("div");
      testLiveSpan.id = "onboardingTestLiveSpan";
      testLiveSpan.style.color = "var(--gold)";
      testLiveSpan.style.fontWeight = "500";
      box.appendChild(testLiveSpan);
    }
    testLiveSpan.textContent = text;
  }
  box.scrollTop = box.scrollHeight;

  verifiedOnboardingTranscription = true;
  const nextBtn1 = $("btnOnboardingNext-1");
  if (nextBtn1) nextBtn1.disabled = false;
}

function initOnboarding() {
  let completed = false;
  try {
    completed = localStorage.getItem('onboarding_completed') === 'true';
  } catch (e) {
    console.error("Storage access failed", e);
  }

  const overlay = $("onboardingOverlay");
  const loadingOverlay = $("appLoadingOverlay");

  if (completed) {
    if (overlay) overlay.classList.add("hidden");
    if (!backendReady && loadingOverlay) {
      loadingOverlay.style.display = "flex";
      loadingOverlay.style.opacity = "1";
      loadingOverlay.style.pointerEvents = "auto";
    }
  } else {
    if (overlay) {
      overlay.classList.remove("hidden");
      showOnboardingStep(0);
    }
    if (loadingOverlay) {
      loadingOverlay.style.display = "none";
    }
    // Request checks immediately if WS is already connected
    if (ws && ws.readyState === WebSocket.OPEN) {
      wsSend({ action: "check_requirements" });
      wsSend({ action: "get_audio_devices" });
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
    try {
      localStorage.setItem('onboarding_completed', 'true');
    } catch (e) {
      console.error("Storage write failed", e);
    }
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