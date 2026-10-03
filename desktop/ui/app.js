(function () {
  const $ = (sel) => document.querySelector(sel);
  const thread = $("#thread");
  const prompt = $("#prompt");
  const teamsEl = $("#teams");
  const modelsNote = $("#models-note");
  const teamsStatus = $("#teams-status");
  const voiceNote = $("#voice-note");
  let messages = [];
  let catalog = [];
  let lastTeamId = "";
  let launchInFlight = false;

  function showPanel(id) {
    document.querySelectorAll(".panel").forEach((p) => {
      const on = p.id === id;
      p.classList.toggle("is-on", on);
      p.hidden = !on;
    });
  }

  function firstRunPending() {
    try {
      return localStorage.getItem("dragon-ai-models-saved") !== "1";
    } catch (_err) {
      return true;
    }
  }

  function addBubble(role, text) {
    const div = document.createElement("div");
    div.className = "bubble " + role;
    div.textContent = text;
    thread.appendChild(div);
    thread.scrollTop = thread.scrollHeight;
  }

  function setTeamsStatus(text) {
    teamsStatus.textContent = text || "";
  }

  function reportLaunch(result) {
    const ok = !!(result && result.ok);
    const err = (result && (result.error || result.message)) || "";
    setTeamsStatus(ok ? (result.message || "Launch started.") : (err || "Launch produced no result."));
    return result || { ok: false, error: "empty-launch-result" };
  }

  async function launchApp() {
    if (launchInFlight) {
      return reportLaunch({ ok: false, error: "Launch is already running." });
    }
    launchInFlight = true;
    setTeamsStatus("Launching Dragon AI Agent...");
    try {
      const res = await fetch("/api/launch", { method: "POST" });
      const data = await res.json();
      if (!data || typeof data.ok !== "boolean") {
        return reportLaunch({ ok: false, error: "Launch returned no result." });
      }
      if (data.ok) {
        showPanel("panel-chat");
        if (!thread.childNodes.length) {
          addBubble("assistant", "Dragon AI Agent is open. Give Dragon AI a task.");
        }
      }
      return reportLaunch(data);
    } catch (err) {
      return reportLaunch({ ok: false, error: "Launch failed. " + err });
    } finally {
      launchInFlight = false;
    }
  }

  $(".hide-sidebar").addEventListener("click", () => {
    document.body.classList.toggle("is-rail-hidden");
  });

  document.querySelectorAll(".rail-tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".rail-tab").forEach((b) => {
        const on = b === btn;
        b.classList.toggle("is-on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      document.querySelectorAll("[data-rail-panel]").forEach((p) => {
        p.hidden = p.getAttribute("data-rail-panel") !== btn.dataset.rail;
      });
    });
  });

  document.querySelectorAll("[data-session]").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("[data-session]").forEach((b) => b.classList.toggle("is-on", b === btn));
      if (btn.hasAttribute("data-open-scheduled-jobs")) {
        openRight("Scheduled Jobs", "about:blank");
        return;
      }
      if (!firstRunPending()) showPanel("panel-chat");
    });
  });

  function openRight(title, url) {
    $("#right-title").textContent = title;
    const frame = $("#bot-screen");
    frame.src = url || "about:blank";
    $("#right-rail").hidden = false;
  }

  $("#right-close").addEventListener("click", () => {
    $("#right-rail").hidden = true;
  });

  function bindBot(btn) {
    btn.addEventListener("dblclick", () => {
      const id = btn.getAttribute("data-bot") || "bot";
      openRight("Bot Screen — " + (btn.textContent || id).trim(), "/bot-screen/");
    });
  }
  document.querySelectorAll("[data-bot]").forEach(bindBot);

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
        "No reply from the local gateway yet.";
      pending.textContent = reply;
      messages.push({ role: "assistant", content: reply });
    } catch (err) {
      pending.textContent = "Could not reach the local gateway. " + err;
    }
  });
  prompt.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && !ev.shiftKey) {
      ev.preventDefault();
      $("#composer").requestSubmit();
    }
  });

  $("#models-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    modelsNote.textContent = "Saving models...";
    try {
      const res = await fetch("/api/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat: $("#chat-model").value,
          image: $("#image-model").value,
        }),
      });
      const data = await res.json();
      if (!data.ok) {
        modelsNote.textContent = data.error || "Could not save models.";
        return;
      }
      try { localStorage.setItem("dragon-ai-models-saved", "1"); } catch (_err) {}
      modelsNote.textContent = "Saved. Opening chat.";
      showPanel("panel-chat");
    } catch (err) {
      modelsNote.textContent = "Could not save models. " + err;
    }
  });

  $("#voice-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    voiceNote.textContent = "Voice engine set to " + ($("#voice-engine").value || "grok-live") + ".";
  });

  $("#composer-wave").addEventListener("click", () => {
    $("#voice-capsule").hidden = false;
  });
  $("#voice-end").addEventListener("click", () => {
    $("#voice-capsule").hidden = true;
  });
  $("#voice-gear").addEventListener("click", () => {
    showPanel("panel-settings");
  });

  function showTeams(open) {
    $("#teams-backdrop").hidden = !open;
    $("#teams-panel").hidden = !open;
    $("[data-dragon-ai-teams-open]").setAttribute("aria-expanded", open ? "true" : "false");
    if (open) loadTeams();
  }
  $("[data-dragon-ai-teams-open]").addEventListener("click", () => showTeams(true));
  $("#teams-close").addEventListener("click", () => showTeams(false));
  $("#teams-backdrop").addEventListener("click", () => showTeams(false));

  async function loadTeams() {
    teamsEl.textContent = "Loading teams...";
    setTeamsStatus("Loading marketplace...");
    try {
      const res = await fetch("/api/teams/");
      const data = await res.json();
      const groups = data.groups || data.teams || [];
      catalog = groups;
      teamsEl.innerHTML = "";
      if (!groups.length) {
        teamsEl.textContent = "Teams helper is starting. Personal Assistant is already installed.";
        setTeamsStatus("No marketplace teams listed yet.");
        return;
      }
      groups.forEach((g) => {
        const id = g.id || g.botGroupId || "";
        if (String(id).toLowerCase() === "personal-assistant") return;
        const card = document.createElement("article");
        card.className = "team";
        card.setAttribute("data-dragon-ai-team-row", "true");
        card.setAttribute("data-dragon-ai-team-id", id);
        const h = document.createElement("h3");
        h.textContent = g.name || g.displayName || id;
        const p = document.createElement("p");
        p.textContent = g.summary || g.blurb || g.description || "";
        const b = document.createElement("button");
        b.className = "primary";
        b.type = "button";
        b.textContent = "Install";
        b.setAttribute("data-dragon-ai-team-apply", "true");
        b.addEventListener("click", async () => {
          lastTeamId = id;
          b.disabled = true;
          setTeamsStatus("Installing " + id + "...");
          try {
            const out = await fetch("/api/teams/marketplace/install", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ id: id }),
            });
            const body = await out.json();
            if (body && body.error) {
              setTeamsStatus(body.message || body.error);
              b.disabled = false;
              return;
            }
            b.textContent = "Installed";
            setTeamsStatus("Installed " + (g.displayName || id) + ".");
            addBotGroup(g);
          } catch (_err) {
            setTeamsStatus("Install failed. Is the Teams Marketplace helper running?");
            b.textContent = "Retry";
            b.disabled = false;
          }
        });
        card.append(h, p, b);
        const seats = document.createElement("ul");
        seats.className = "seats";
        seats.setAttribute("data-dragon-ai-team-seats", "true");
        (g.bots || []).forEach((bot) => {
          const li = document.createElement("li");
          li.textContent = bot.title || bot.id || "";
          seats.appendChild(li);
        });
        if (seats.childNodes.length) card.appendChild(seats);
        teamsEl.appendChild(card);
      });
      setTeamsStatus("Install a team to add its bots, or Launch a pack.");
    } catch (_err) {
      teamsEl.textContent = "Teams Marketplace helper is not up yet. It starts with Dragon AI Agent.";
      setTeamsStatus("Teams Marketplace helper is not running on 127.0.0.1:8653.");
    }
  }

  function addBotGroup(g) {
    const bots = $("#rail-bots");
    const id = g.id || "";
    if (!id || bots.querySelector('[data-group="' + id + '"]')) return;
    const sec = document.createElement("section");
    sec.className = "group";
    sec.setAttribute("data-group", id);
    const h = document.createElement("h3");
    h.textContent = g.displayName || g.name || id;
    sec.appendChild(h);
    (g.bots || [{ id: id, title: g.displayName || id }]).forEach((bot) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "bot";
      b.setAttribute("data-bot", bot.id || id);
      b.textContent = bot.title || bot.id || id;
      bindBot(b);
      sec.appendChild(b);
    });
    bots.appendChild(sec);
  }

  $("#teams-launch").addEventListener("click", async () => {
    const ids = lastTeamId ? [lastTeamId] : [];
    if (!ids.length) {
      reportLaunch({ ok: false, error: "Install a team first, then Launch." });
      return;
    }
    setTeamsStatus("Launching " + ids.join(", ") + "...");
    try {
      const res = await fetch("/api/teams/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: ids }),
      });
      const data = await res.json();
      if (data && data.error) {
        reportLaunch({ ok: false, error: data.message || data.error });
        return;
      }
      const app = await launchApp();
      if (app.ok) showTeams(false);
    } catch (_err) {
      reportLaunch({ ok: false, error: "Launch failed. Is the Teams Marketplace helper running?" });
    }
  });

  if (firstRunPending()) {
    showPanel("panel-models");
  } else {
    showPanel("panel-chat");
  }
})();
