(function () {
  const $ = (sel) => document.querySelector(sel);
  const thread = $("#thread");
  const status = $("#status");
  const prompt = $("#prompt");
  const teamsEl = $("#teams");
  const modelsNote = $("#models-note");
  let messages = [];

  function setStatus(text) {
    status.textContent = text;
  }

  function addBubble(role, text) {
    const div = document.createElement("div");
    div.className = "bubble " + role;
    div.textContent = text;
    thread.appendChild(div);
    thread.scrollTop = thread.scrollHeight;
  }

  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => {
        const on = b === btn;
        b.classList.toggle("is-on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      document.querySelectorAll(".panel").forEach((p) => {
        const on = p.id === "panel-" + btn.dataset.tab;
        p.classList.toggle("is-on", on);
        p.hidden = !on;
      });
      if (btn.dataset.tab === "teams") loadTeams();
    });
  });

  async function poll() {
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

  $("#composer").addEventListener("submit", async (ev) => {
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
          model: $("#chat-model").value || "grok-4.6",
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

  $("#models-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    modelsNote.textContent = "Saved in this window. Gateway defaults also come from the in-app Models apply on launch.";
  });

  async function loadTeams() {
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

  poll();
  setInterval(poll, 4000);
})();
