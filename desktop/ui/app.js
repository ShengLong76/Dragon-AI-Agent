(function () {
  const $ = (sel) => document.querySelector(sel);
  const KEY = "dragon-ai-onboarded";
  const MODEL_KEY = "dragon-ai-chat-model";
  const DEFAULT_MODEL = "grok-4.7";
  const thread = $("#thread");
  const status = $("#status");
  const prompt = $("#prompt");
  const teamsEl = $("#teams");
  const modelEl = $("#chat-model");
  const modelLabel = $("#default-model");
  let messages = [];

  function currentModel() {
    return (modelEl && modelEl.value) || localStorage.getItem(MODEL_KEY) || DEFAULT_MODEL;
  }

  function setModel(id) {
    const next = id || DEFAULT_MODEL;
    if (modelEl) modelEl.value = next;
    if (modelLabel) modelLabel.textContent = next;
    try { localStorage.setItem(MODEL_KEY, next); } catch (_err) {}
  }

  function showScreen(id) {
    document.querySelectorAll(".screen").forEach((el) => {
      const on = el.id === id;
      el.classList.toggle("is-on", on);
      el.hidden = !on;
    });
    document.body.setAttribute("data-screen", id.replace("screen-", ""));
  }

  function persistHome() {
    try { localStorage.setItem(KEY, "1"); } catch (_err) {}
  }

  function selectRail(name) {
    document.querySelectorAll(".rail-tab").forEach((btn) => {
      const on = btn.dataset.rail === name;
      btn.classList.toggle("is-on", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    const bots = $("#rail-bots");
    const sessions = $("#rail-sessions");
    if (bots) bots.hidden = name !== "bots";
    if (sessions) sessions.hidden = name !== "sessions";
  }

  function setStatus(text) {
    if (status) status.textContent = text;
  }

  function addBubble(role, text) {
    if (!thread) return;
    const div = document.createElement("div");
    div.className = "bubble " + role;
    div.textContent = text;
    thread.appendChild(div);
    thread.scrollTop = thread.scrollHeight;
  }

  function connectGrok() {
    showScreen("screen-confirm");
    setModel(currentModel() || DEFAULT_MODEL);
    const note = $("#confirm-status");
    if (note) note.textContent = "XAI Grok OAuth (SuperGrok / Premium+) connected";
  }

  function beginHome() {
    persistHome();
    showScreen("screen-home");
    selectRail("bots");
    mountVm();
    poll();
  }

  function mountVm() {
    const frame = $("#vm-frame");
    const fallback = $("#vm-fallback");
    if (!frame) return;
    const url = "http://127.0.0.1:8650/";
    frame.src = url;
    const timer = setTimeout(() => {
      if (fallback) fallback.hidden = false;
      frame.hidden = true;
    }, 1500);
    frame.addEventListener("load", () => {
      try {
        const href = frame.contentWindow && frame.contentWindow.location.href;
        if (href && href !== "about:blank") {
          clearTimeout(timer);
          frame.hidden = false;
          if (fallback) fallback.hidden = true;
        }
      } catch (_err) {
        clearTimeout(timer);
        frame.hidden = false;
        if (fallback) fallback.hidden = true;
      }
    }, { once: true });
  }

  document.querySelectorAll("[data-provider]").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.provider === "xai-grok") {
        connectGrok();
        return;
      }
      addNotice("Connect xAI Grok to start. Grok is the recommended provider.");
    });
  });

  function addNotice(text) {
    const list = $("#provider-list");
    if (!list) return;
    let note = document.getElementById("provider-note");
    if (!note) {
      note = document.createElement("p");
      note.id = "provider-note";
      note.className = "lede";
      list.after(note);
    }
    note.textContent = text;
  }

  const later = $("#choose-later");
  if (later) {
    later.addEventListener("click", () => {
      addNotice("Pick xAI Grok to continue. It is the recommended provider.");
    });
  }
  const haveKey = $("#have-key");
  if (haveKey) {
    haveKey.addEventListener("click", () => {
      addNotice("Use xAI Grok OAuth (SuperGrok / Premium+). No pasted key is required.");
    });
  }

  const change = $("#change-model");
  if (change) {
    change.addEventListener("click", () => {
      const picker = $("#model-picker");
      if (picker) picker.hidden = !picker.hidden;
    });
  }
  if (modelEl) {
    modelEl.addEventListener("change", () => setModel(modelEl.value));
  }
  const begin = $("#begin");
  if (begin) begin.addEventListener("click", beginHome);

  document.querySelectorAll(".rail-tab").forEach((btn) => {
    btn.addEventListener("click", () => selectRail(btn.dataset.rail));
  });

  const teamsOpen = $("#teams-open");
  const teamsDialog = $("#teams-dialog");
  const teamsClose = $("#teams-close");
  if (teamsOpen && teamsDialog) {
    teamsOpen.addEventListener("click", () => {
      if (typeof teamsDialog.showModal === "function") teamsDialog.showModal();
      loadTeams();
    });
  }
  if (teamsClose && teamsDialog) {
    teamsClose.addEventListener("click", () => teamsDialog.close());
  }

  const composer = $("#composer");
  if (composer) {
    composer.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const text = prompt.value.trim();
      if (!text) return;
      prompt.value = "";
      addBubble("user", text);
      messages.push({ role: "user", content: text });
      addBubble("assistant", "Thinking...");
      const pending = thread.lastChild;
      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: currentModel(),
            messages: messages,
          }),
        });
        const data = await res.json();
        const reply =
          (data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content) ||
          data.error ||
          "No reply from the local gateway yet. Wait until status says Gateway ready.";
        pending.textContent = reply;
        messages.push({ role: "assistant", content: reply });
      } catch (err) {
        pending.textContent = "Could not reach the local gateway. " + err;
      }
    });
  }

  async function poll() {
    if (!status) return;
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      if (data.gateway && data.gateway.ok) {
        setStatus(data.desktop && data.desktop.ok ? "Gateway ready" : "Gateway up, Bot Screen starting...");
      } else {
        setStatus("Starting gateway...");
      }
    } catch (_err) {
      setStatus("Starting Dragon AI Agent...");
    }
  }

  async function loadTeams() {
    if (!teamsEl) return;
    teamsEl.textContent = "Loading teams...";
    try {
      const res = await fetch("/api/teams/");
      const data = await res.json();
      const groups = data.groups || data.teams || [];
      teamsEl.innerHTML = "";
      if (!groups.length) {
        teamsEl.textContent = "Teams helper is starting. Personal Assistant is already installed.";
        return;
      }
      groups.forEach((g) => {
        const id = g.id || g.botGroupId || "";
        if (String(id).toLowerCase() === "personal-assistant") return;
        const card = document.createElement("article");
        card.className = "team";
        const h = document.createElement("h3");
        h.textContent = g.name || g.displayName || id;
        const p = document.createElement("p");
        p.textContent = g.summary || g.description || "";
        const b = document.createElement("button");
        b.className = "primary";
        b.type = "button";
        b.textContent = "Install";
        b.addEventListener("click", async () => {
          b.disabled = true;
          try {
            await fetch("/api/teams/marketplace/install", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: id }),
            });
            b.textContent = "Installed";
          } catch (_err) {
            b.textContent = "Retry";
            b.disabled = false;
          }
        });
        card.append(h, p, b);
        teamsEl.appendChild(card);
      });
    } catch (_err) {
      teamsEl.textContent = "Teams Marketplace helper is not up yet. It starts with Dragon AI Agent.";
    }
  }

  const params = new URLSearchParams(location.search);
  const forceFirst = params.get("first-run") === "1" || params.get("reset") === "1";
  if (forceFirst) {
    try { localStorage.removeItem(KEY); } catch (_err) {}
  }
  setModel(localStorage.getItem(MODEL_KEY) || DEFAULT_MODEL);
  const already = !forceFirst && localStorage.getItem(KEY) === "1";
  if (already) {
    beginHome();
  } else {
    showScreen("screen-providers");
  }
  setInterval(() => {
    if (document.body.getAttribute("data-screen") === "home") poll();
  }, 4000);
})();
