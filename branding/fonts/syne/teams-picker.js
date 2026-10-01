(function () {
  var API = "http://127.0.0.1:8653";
  function $(sel, root) { return (root || document).querySelector(sel); }
  function mount() {
    if (document.querySelector("[data-dragon-ai-teams-root]")) return;
    var host = document.querySelector("[data-dragon-ai-sidebar-brand]")
      || document.querySelector('[data-slot="sidebar-header"]')
      || document.querySelector('[data-slot="sidebar-inner"]');
    if (!host) return;
    var root = document.createElement("div");
    root.setAttribute("data-dragon-ai-teams-root", "true");
    var open = document.createElement("button");
    open.type = "button";
    open.textContent = "Teams";
    open.setAttribute("data-dragon-ai-teams-open", "true");
    open.setAttribute("aria-haspopup", "dialog");
    var panel = document.createElement("div");
    panel.setAttribute("data-dragon-ai-teams-panel", "true");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Teams");
    panel.hidden = true;
    panel.innerHTML = '<header><h2>Teams</h2><p>Apply a multi-bot team. Personal Assistant is already installed. Bots file under that team name, not Unassigned.</p></header><div data-dragon-ai-teams-list></div><label>Import custom zip or JSON<input type="file" accept=".zip,.json,application/json,application/zip" data-dragon-ai-teams-import></label><p data-dragon-ai-teams-status role="status"></p><button type="button" data-dragon-ai-teams-close>Close</button>';
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
    var row = document.querySelector("[data-dragon-ai-sidebar-row]");
    if (row) {
      row.appendChild(root);
    } else if (host.getAttribute && host.getAttribute("data-dragon-ai-sidebar-brand") && host.parentNode) {
      host.parentNode.insertBefore(root, host.nextSibling);
    } else {
      host.appendChild(root);
    }
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
