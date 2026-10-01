(function () {
  var API = "http://127.0.0.1:8653";
  var LABEL = "Teams Marketplace";
  function $(sel, root) { return (root || document).querySelector(sel); }
  function querySlot(name) {
    return document.querySelector('[data-slot="' + name + '"]');
  }
  function findColumnHost() {
    return querySlot("sidebar-header")
      || document.querySelector('[data-sidebar="header"]')
      || querySlot("sidebar-inner")
      || querySlot("sidebar-container")
      || querySlot("sidebar")
      || document.querySelector('[data-sidebar="sidebar"]');
  }
  function findSessionsBotsStrip() {
    var nodes = document.querySelectorAll('[role="tab"],button,a');
    var row = null;
    var i;
    for (i = 0; i < nodes.length; i++) {
      var t = (nodes[i].textContent || "").replace(/\s+/g, " ").trim();
      if (/^(bots|sessions)$/i.test(t)) {
        row = nodes[i].parentElement || nodes[i];
        if (/^bots$/i.test(t)) return row;
      }
    }
    return row;
  }
  function pinFixedHost(host) {
    var top = 48;
    var strip = findSessionsBotsStrip();
    if (strip && strip.getBoundingClientRect) {
      var box = strip.getBoundingClientRect();
      if (box && box.bottom > 0) {
        top = Math.max(8, Math.round(box.bottom + 8));
      }
    }
    host.setAttribute("data-dragon-ai-sidebar-fixed", "true");
    host.style.cssText = "position:fixed;z-index:40;top:" + top + "px;left:0;width:16rem;max-width:16rem;min-width:16rem;box-sizing:border-box;margin:0;padding:0;pointer-events:none;background:transparent;border:0;";
  }
  function ensureFixedHost() {
    var existing = document.querySelector("[data-dragon-ai-sidebar-fixed]");
    if (existing) {
      pinFixedHost(existing);
      return existing;
    }
    if (!document.body) return null;
    var host = document.createElement("div");
    pinFixedHost(host);
    document.body.appendChild(host);
    return host;
  }
  function findDragonSidebarHost() {
    return findColumnHost() || ensureFixedHost();
  }
  function place(root) {
    var row = document.querySelector("[data-dragon-ai-sidebar-row]");
    if (row) {
      if (root.parentNode !== row) row.appendChild(root);
      return;
    }
    var host = document.querySelector("[data-dragon-ai-sidebar-brand]")
      || findDragonSidebarHost();
    if (!host) return;
    if (host.getAttribute && host.getAttribute("data-dragon-ai-sidebar-brand") && host.parentNode) {
      if (root.parentNode !== host.parentNode) {
        host.parentNode.insertBefore(root, host.nextSibling);
      }
      return;
    }
    if (root.parentNode !== host) host.appendChild(root);
  }
  function mount() {
    var existing = document.querySelector("[data-dragon-ai-teams-root]");
    if (existing) {
      place(existing);
      return;
    }
    var root = document.createElement("div");
    root.setAttribute("data-dragon-ai-teams-root", "true");
    root.style.pointerEvents = "auto";
    var open = document.createElement("button");
    open.type = "button";
    open.textContent = LABEL;
    open.setAttribute("data-dragon-ai-teams-open", "true");
    open.setAttribute("aria-haspopup", "dialog");
    open.setAttribute("aria-label", LABEL);
    var panel = document.createElement("div");
    panel.setAttribute("data-dragon-ai-teams-panel", "true");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", LABEL);
    panel.hidden = true;
    panel.innerHTML = '<header><h2>Teams Marketplace</h2><p>Apply a multi-bot team. Personal Assistant is already installed. Bots file under that team name, not Unassigned.</p></header><div data-dragon-ai-teams-list></div><label>Import custom zip or JSON<input type="file" accept=".zip,.json,application/json,application/zip" data-dragon-ai-teams-import></label><p data-dragon-ai-teams-status role="status"></p><button type="button" data-dragon-ai-teams-close>Close</button>';
    function setStatus(t) {
      var s = $("[data-dragon-ai-teams-status]", panel);
      if (s) s.textContent = t || "";
    }
    function show() { panel.hidden = false; panel.removeAttribute("hidden"); load(); }
    function hide() { panel.hidden = true; panel.setAttribute("hidden", ""); }
    function reloadRoster() {
      hide();
      try { location.reload(); } catch (e) {
        try { window.location.href = window.location.href; } catch (e2) {}
      }
    }
    function finishApply() { hide(); reloadRoster(); }
    function card(team) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("data-dragon-ai-team-id", team.id || "");
      b.innerHTML = "<strong></strong><span></span>";
      b.querySelector("strong").textContent = team.displayName || team.name || team.id;
      b.querySelector("span").textContent = team.departmentJob || "";
      b.addEventListener("click", function () { apply(team.id); });
      return b;
    }
    function load() {
      setStatus("Loading teams…");
      fetch(API + "/api/teams").then(function (r) { return r.json(); }).then(function (data) {
        var list = $("[data-dragon-ai-teams-list]", panel);
        if (!list) return;
        list.textContent = "";
        (data.teams || []).forEach(function (t) { list.appendChild(card(t)); });
        setStatus((data.teams || []).length ? "Pick a team to apply." : "No teams listed.");
      }).catch(function () { setStatus("Teams helper is not running on 127.0.0.1:8653."); });
    }
    function apply(id) {
      setStatus("Applying " + id + "…");
      fetch(API + "/api/teams/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id })
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (data.error) { setStatus(data.message || data.error); return; }
        finishApply();
      }).catch(function () { setStatus("Apply failed. Is the Teams helper running?"); });
    }
    function importFile(file) {
      if (!file) return;
      setStatus("Importing " + file.name + "…");
      var reader = new FileReader();
      reader.onload = function () {
        var bytes = new Uint8Array(reader.result);
        var bin = "";
        for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
        fetch(API + "/api/teams/import", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ filename: file.name, contentBase64: btoa(bin) })
        }).then(function (r) { return r.json(); }).then(function (data) {
          if (data.error) { setStatus(data.message || data.error); return; }
          finishApply();
        }).catch(function () { setStatus("Import failed."); });
      };
      reader.readAsArrayBuffer(file);
    }
    open.addEventListener("click", show);
    $("[data-dragon-ai-teams-close]", panel).addEventListener("click", hide);
    var inp = $("[data-dragon-ai-teams-import]", panel);
    if (inp) inp.addEventListener("change", function () { importFile(inp.files && inp.files[0]); });
    root.appendChild(open);
    if (document.body) { document.body.appendChild(panel); } else { root.appendChild(panel); }
    place(root);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
  try {
    new MutationObserver(mount).observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) {}
})();
