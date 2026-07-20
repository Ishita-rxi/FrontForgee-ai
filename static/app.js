const state = {
  sessionId: null,
  questions: [],
  presets: { color_presets: [], style_variants: [] },
  files: [],
  components: [],
  selectedComponent: null,
  buildPollTimer: null,
  swapPollTimer: null,
};

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = body.detail || `Request failed: ${res.status}`;

    // The server keeps sessions in memory only. A free-tier host that
    // spins down after inactivity wipes that memory on wake-up, so a
    // session id the page is still holding can go stale. Rather than
    // surface a confusing raw error, recover by starting a new session
    // and asking the person to retry, once.
    if (res.status === 404 && /session/i.test(message) && !options._retriedAfterSessionReset) {
      await init();
      throw new Error(
        "Your session had expired (the free hosting tier went to sleep and lost it). " +
        "A new session has been started — please try that action again."
      );
    }

    throw new Error(message);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------
document.querySelectorAll("nav.tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav.tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------
async function init() {
  const data = await api("/api/session", { method: "POST" });
  state.sessionId = data.session_id;

  const npmBadge = document.getElementById("npm-status");
  if (data.npm_available) {
    npmBadge.textContent = `npm ready (node ${data.node_version})`;
    npmBadge.className = "badge success";
  } else {
    npmBadge.textContent = "npm not found on this host";
    npmBadge.className = "badge error";
  }

  const presetData = await api("/api/presets");
  state.presets = presetData;

  await refreshProviderStatus();
}
init();

async function refreshProviderStatus() {
  const status = await api(`/api/llm-status/${state.sessionId}`);
  const el = document.getElementById("provider-status");
  const badgeClass = status.ready ? "badge success" : "badge warn";
  el.innerHTML =
    `<span class="${badgeClass}">${status.provider}</span> &nbsp; ${status.detail}`;

  // The Groq key field is only relevant when Groq is actually the active
  // provider — showing it for an Ollama setup would just be confusing.
  document.getElementById("groq-key-card").classList.toggle("hidden", status.provider !== "groq");
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------
document.getElementById("btn-save-key").addEventListener("click", async () => {
  const key = document.getElementById("api-key").value;
  await api("/api/settings", {
    method: "POST",
    body: JSON.stringify({ session_id: state.sessionId, api_key: key }),
  });
  document.getElementById("key-status").textContent = key ? "Key saved for this session." : "Key cleared.";
  await refreshProviderStatus();
});

// ---------------------------------------------------------------------------
// Clarification
// ---------------------------------------------------------------------------
document.getElementById("btn-clarify").addEventListener("click", async () => {
  const prompt = document.getElementById("prompt").value.trim();
  if (!prompt) return;
  const btn = document.getElementById("btn-clarify");
  btn.textContent = "Thinking...";
  btn.disabled = true;
  try {
    const data = await api("/api/clarify", {
      method: "POST",
      body: JSON.stringify({ session_id: state.sessionId, prompt }),
    });
    state.questions = data.questions;
    renderQuestions();
  } catch (err) {
    alert(err.message);
  } finally {
    btn.textContent = "Get clarifying questions";
    btn.disabled = false;
  }
});

document.getElementById("btn-skip").addEventListener("click", () => {
  state.questions = [
    { question: "Which framework should be used?", options: ["React (Vite)", "Next.js"], default: "React (Vite)" },
    { question: "Which styling approach?", options: ["Tailwind CSS", "Bootstrap", "Material UI"], default: "Tailwind CSS" },
    { question: "Which starting color theme?", options: ["Ocean Blue", "Sunset", "Forest", "Royal Violet", "Minimal Dark"], default: "Ocean Blue" },
    { question: "How complex should the generated app be?", options: ["Minimal (2-3 components)", "Standard (5-8 components)", "Rich (9+ components)"], default: "Standard (5-8 components)" },
  ];
  renderQuestions();
});

function renderQuestions() {
  const container = document.getElementById("clarify-questions");
  container.innerHTML = "";
  state.questions.forEach((q, i) => {
    const label = document.createElement("label");
    label.textContent = q.question;
    const select = document.createElement("select");
    select.id = `q-${i}`;
    (q.options || []).forEach((opt) => {
      const option = document.createElement("option");
      option.value = opt;
      option.textContent = opt;
      if (opt === q.default) option.selected = true;
      select.appendChild(option);
    });
    container.appendChild(label);
    container.appendChild(select);
  });
  document.getElementById("clarify-card").classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// Generation
// ---------------------------------------------------------------------------
document.getElementById("btn-generate").addEventListener("click", async () => {
  const prompt = document.getElementById("prompt").value.trim();
  const answers = {};
  state.questions.forEach((q, i) => {
    answers[q.question] = document.getElementById(`q-${i}`).value;
  });

  document.getElementById("generation-progress").classList.remove("hidden");
  document.getElementById("generation-summary").classList.add("hidden");
  document.getElementById("gen-spinner").classList.remove("hidden");
  document.getElementById("gen-status-label").textContent = "Running agent pipeline...";
  document.getElementById("generation-log").innerHTML = "";

  try {
    await api("/api/generate", {
      method: "POST",
      body: JSON.stringify({ session_id: state.sessionId, prompt, answers }),
    });
  } catch (err) {
    alert(err.message);
    return;
  }

  pollGeneration();
});

function pollGeneration() {
  const timer = setInterval(async () => {
    const data = await api(`/api/generate-status/${state.sessionId}`);
    renderGenerationLog(data.log);

    if (data.status === "success") {
      clearInterval(timer);
      document.getElementById("gen-spinner").classList.add("hidden");
      document.getElementById("gen-status-label").textContent = "Pipeline complete.";
      onGenerationComplete(data);
    } else if (data.status === "failed") {
      clearInterval(timer);
      document.getElementById("gen-spinner").classList.add("hidden");
      document.getElementById("gen-status-label").textContent = "Pipeline failed. See log below.";
    }
  }, 1200);
}

function renderGenerationLog(log) {
  const container = document.getElementById("generation-log");
  container.innerHTML = "";
  log.forEach((line, i) => {
    const div = document.createElement("div");
    div.className = "log-line" + (i === log.length - 1 ? " latest" : "");
    div.textContent = line;
    container.appendChild(div);
  });
}

async function onGenerationComplete(data) {
  document.getElementById("generation-summary").classList.remove("hidden");
  document.getElementById("summary-app-name").textContent = data.plan.app_name || "Generated app";
  document.getElementById("summary-pages").textContent = `${data.plan.pages.length} pages`;
  document.getElementById("summary-components").textContent = `${data.plan.components.length} components`;
  document.getElementById("summary-clarifications").textContent = `${data.clarification_count} clarification prompt(s)`;

  state.files = data.files;
  state.components = data.components;

  populateFilesTab();
  populateSwapTab();
  populateReviewTab(data);
  document.getElementById("download-project").href = `/download/${state.sessionId}/project.zip`;
}

// ---------------------------------------------------------------------------
// Project Files tab
// ---------------------------------------------------------------------------
function populateFilesTab() {
  const select = document.getElementById("file-select");
  select.innerHTML = "";
  state.files.forEach((f) => {
    const opt = document.createElement("option");
    opt.value = f;
    opt.textContent = f;
    select.appendChild(opt);
  });
  select.onchange = loadSelectedFile;
  loadSelectedFile();
}

async function loadSelectedFile() {
  const path = document.getElementById("file-select").value;
  if (!path) return;
  const data = await api(`/api/file/${state.sessionId}?path=${encodeURIComponent(path)}`);
  document.getElementById("file-content").textContent = data.content;
}

// ---------------------------------------------------------------------------
// Style Swapper tab
// ---------------------------------------------------------------------------
function populateSwapTab() {
  const select = document.getElementById("component-select");
  select.innerHTML = "";
  state.components.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    select.appendChild(opt);
  });
  select.onchange = () => renderSwapControls();

  const presetContainer = document.getElementById("preset-buttons");
  presetContainer.innerHTML = "";
  state.presets.color_presets.forEach((preset) => {
    const btn = document.createElement("button");
    btn.className = "secondary";
    btn.textContent = preset;
    btn.onclick = () => applySwap("/api/swap-color", preset);
    btn.dataset.preset = preset;
    presetContainer.appendChild(btn);
  });

  const variantContainer = document.getElementById("variant-buttons");
  variantContainer.innerHTML = "";
  state.presets.style_variants.forEach((variant) => {
    const btn = document.createElement("button");
    btn.className = "secondary";
    btn.textContent = variant;
    btn.onclick = () => applySwap("/api/swap-variant", variant);
    btn.dataset.variant = variant;
    variantContainer.appendChild(btn);
  });

  renderSwapControls();
}

async function renderSwapControls() {
  state.selectedComponent = document.getElementById("component-select").value;
  if (!state.selectedComponent) return;
  const path = `src/components/${state.selectedComponent}.jsx`;
  const data = await api(`/api/file/${state.sessionId}?path=${encodeURIComponent(path)}`);
  document.getElementById("swap-code").textContent = data.content;
}

async function applySwap(endpoint, value) {
  const isColor = endpoint.includes("color");
  const data = await api(endpoint, {
    method: "POST",
    body: JSON.stringify({ session_id: state.sessionId, component: state.selectedComponent, value }),
  });
  document.getElementById("swap-code").textContent = data.code;

  document.querySelectorAll(isColor ? "#preset-buttons button" : "#variant-buttons button").forEach((b) => {
    b.classList.toggle("selected", b.textContent === value);
  });

  triggerSwapRebuild();
}

document.getElementById("btn-apply-all").addEventListener("click", async () => {
  const selected = document.querySelector("#preset-buttons button.selected");
  const preset = selected ? selected.textContent : state.presets.color_presets[0];
  await api("/api/swap-color-all", {
    method: "POST",
    body: JSON.stringify({ session_id: state.sessionId, preset }),
  });
  renderSwapControls();
  triggerSwapRebuild();
});

async function triggerSwapRebuild() {
  try {
    await api(`/api/build/${state.sessionId}`, { method: "POST" });
  } catch (err) {
    return; // npm not available — silently skip the live rebuild
  }
  if (state.swapPollTimer) clearInterval(state.swapPollTimer);
  state.swapPollTimer = setInterval(async () => {
    const data = await api(`/api/build-status/${state.sessionId}`);
    if (data.status === "success") {
      clearInterval(state.swapPollTimer);
      const frame = document.getElementById("swap-preview-frame");
      frame.classList.remove("hidden");
      frame.src = `/preview/${state.sessionId}/index.html?v=${data.build_version}`;
    } else if (data.status === "failed") {
      clearInterval(state.swapPollTimer);
    }
  }, 1000);
}

// ---------------------------------------------------------------------------
// Live Preview tab (manual build button)
// ---------------------------------------------------------------------------
document.getElementById("btn-build").addEventListener("click", async () => {
  const box = document.getElementById("build-status-box");
  box.innerHTML = '<span class="spinner"></span> Starting build...';
  document.getElementById("build-log").classList.add("hidden");

  try {
    await api(`/api/build/${state.sessionId}`, { method: "POST" });
  } catch (err) {
    box.innerHTML = `<span class="badge error">${err.message}</span>`;
    return;
  }

  if (state.buildPollTimer) clearInterval(state.buildPollTimer);
  state.buildPollTimer = setInterval(async () => {
    const data = await api(`/api/build-status/${state.sessionId}`);
    if (data.status === "installing") {
      box.innerHTML = '<span class="spinner"></span> Running npm install (first time can take a minute)...';
    } else if (data.status === "building") {
      box.innerHTML = '<span class="spinner"></span> Running npm run build...';
    } else if (data.status === "success") {
      clearInterval(state.buildPollTimer);
      box.innerHTML = '<span class="badge success">Build succeeded</span>';
      const frame = document.getElementById("preview-frame");
      frame.classList.remove("hidden");
      frame.src = `/preview/${state.sessionId}/index.html?v=${data.build_version}`;
      document.getElementById("download-dist").href = `/download/${state.sessionId}/dist.zip`;
      document.getElementById("download-dist").classList.remove("hidden");
    } else if (data.status === "failed") {
      clearInterval(state.buildPollTimer);
      box.innerHTML = '<span class="badge error">Build failed</span>';
      const log = document.getElementById("build-log");
      log.textContent = data.log;
      log.classList.remove("hidden");
    }
  }, 1200);
});

// ---------------------------------------------------------------------------
// Review & Export tab
// ---------------------------------------------------------------------------
function populateReviewTab(data) {
  const issuesEl = document.getElementById("static-issues");
  if (data.static_issues.length) {
    issuesEl.innerHTML = `<span class="badge warn">${data.static_issues.length} static issue(s) found</span>` +
      "<ul>" + data.static_issues.map((i) => `<li>${i}</li>`).join("") + "</ul>";
  } else {
    issuesEl.innerHTML = '<span class="badge success">No static issues found</span>';
  }
  document.getElementById("review-text").textContent = data.review_text;
}
