(function () {
  // Expected DOM order: lockup → Teams Marketplace → Sessions/Bots
  var API = "http://127.0.0.1:8653";
  var LABEL = "Teams Marketplace";
  var CHROME_STYLE = "display:flex;flex-direction:column;align-items:stretch;width:100%;min-height:96px;box-sizing:border-box;margin:0;padding:0;flex:0 0 auto;order:-1;position:relative;z-index:1;pointer-events:auto;background:transparent;border:0;";
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }
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
  function labelOf(el) {
    return (el.textContent || "").replace(/\s+/g, " ").trim();
  }
  function findBotsTab() {
    var tabs = document.querySelectorAll('[role="tab"]');
    var fallback = null;
    var i;
    for (i = 0; i < tabs.length; i++) {
      var t = labelOf(tabs[i]);
      if (/^bots$/i.test(t)) return tabs[i];
      if (/^sessions$/i.test(t)) fallback = fallback || tabs[i];
    }
    var nodes = document.querySelectorAll("button, a, [role='tablist'] *");
    for (i = 0; i < nodes.length; i++) {
      if (/^bots$/i.test(labelOf(nodes[i]))) return nodes[i];
    }
    return fallback;
  }
  function findTabStrip(tab) {
    var node = tab;
    var hops = 0;
    while (node && hops < 8) {
      var parent = node.parentElement;
      if (!parent) break;
      var kids = parent.children;
      var bots = 0;
      var sessions = 0;
      var i;
      for (i = 0; i < kids.length; i++) {
        var label = labelOf(kids[i]);
        if (/^bots$/i.test(label)) bots += 1;
        if (/^sessions$/i.test(label)) sessions += 1;
      }
      if (bots && sessions) return parent;
      node = parent;
      hops += 1;
    }
    return tab.parentElement || tab;
  }
  function isAppShell(el) {
    if (!el) return true;
    var slot = el.getAttribute && el.getAttribute("data-slot");
    if (slot === "sidebar-wrapper") return true;
    var tag = (el.tagName || "").toLowerCase();
    return tag === "body" || tag === "html";
  }
  function isTabRow(el) {
    if (!el || !el.children) return false;
    var bots = 0;
    var sessions = 0;
    var i;
    for (i = 0; i < el.children.length; i++) {
      var t = labelOf(el.children[i]);
      if (/^bots$/i.test(t)) bots += 1;
      if (/^sessions$/i.test(t)) sessions += 1;
    }
    return !!(bots && sessions);
  }
  function looksHorizontalChrome(el) {
    if (isTabRow(el)) return true;
    try {
      var cs = window.getComputedStyle(el);
      var dir = cs && cs.flexDirection;
      if (dir === "row" || dir === "row-reverse") {
        var box = el.getBoundingClientRect && el.getBoundingClientRect();
        if (box && box.height > 0 && box.height < 72) return true;
      }
    } catch (e) {}
    return false;
  }
  function findInFlowColumn() {
    var tab = findBotsTab();
    if (!tab) return null;
    var strip = findTabStrip(tab);
    if (!strip) return null;
    var roster = document.querySelector('[data-slot="bots-roster"]');
    var node = strip.parentElement;
    var hops = 0;
    var fallback = null;
    while (node && hops < 14) {
      if (isAppShell(node)) break;
      if (!looksHorizontalChrome(node) && node.contains(strip)) {
        if (roster && node.contains(roster)) return node;
        if (node.children && node.children.length >= 2) fallback = fallback || node;
      }
      node = node.parentElement;
      hops += 1;
    }
    return fallback;
  }
  function lockupHeight() {
    var measured = document.querySelector("[data-dragon-ai-sidebar-chrome]")
      || document.querySelector("[data-dragon-ai-sidebar-row]");
    if (measured && measured.getBoundingClientRect) {
      var height = measured.getBoundingClientRect().height;
      if (height > 24) return Math.max(96, Math.ceil(height + 8));
    }
    return 96;
  }
  function pinChrome(chrome) {
    chrome.setAttribute("data-dragon-ai-sidebar-chrome", "true");
    chrome.removeAttribute("data-dragon-ai-sidebar-fixed");
    chrome.style.cssText = CHROME_STYLE;
  }
  function bumpStickyStrip(strip, height) {
    if (!strip) return;
    try {
      var cs = window.getComputedStyle(strip);
      if (!cs) return;
      if (cs.position !== "sticky" && cs.position !== "absolute" && cs.position !== "fixed") return;
      if (strip.getAttribute("data-dragon-ai-tab-offset") === String(height)) return;
      strip.setAttribute("data-dragon-ai-tab-offset", String(height));
      strip.style.top = height + "px";
    } catch (e) {}
  }
  function ensureInFlowHost() {
    var column = findInFlowColumn();
    if (!column) return null;
    var chrome = document.querySelector("[data-dragon-ai-sidebar-chrome]");
    if (!chrome) chrome = document.createElement("div");
    pinChrome(chrome);
    if (chrome.parentElement !== column || column.firstElementChild !== chrome) {
      column.insertBefore(chrome, column.firstChild);
    }
    var spacer = document.querySelector("[data-dragon-ai-sidebar-clearance]");
    if (spacer && spacer.parentElement) spacer.parentElement.removeChild(spacer);
    var fixed = document.querySelector("[data-dragon-ai-sidebar-fixed]");
    if (fixed && fixed !== chrome) {
      var row = document.querySelector("[data-dragon-ai-sidebar-row]");
      if (row && !chrome.contains(row)) chrome.insertBefore(row, chrome.firstChild);
      if (fixed.parentElement) fixed.parentElement.removeChild(fixed);
    }
    var tab = findBotsTab();
    bumpStickyStrip(tab ? findTabStrip(tab) : null, lockupHeight());
    return chrome;
  }
  function ensureClearance(height) {
    var column = findInFlowColumn();
    var tab = findBotsTab();
    var strip = tab ? findTabStrip(tab) : null;
    var parent = column || (strip && strip.parentElement);
    if (!parent) return null;
    var spacer = document.querySelector("[data-dragon-ai-sidebar-clearance]");
    if (!spacer) {
      spacer = document.createElement("div");
      spacer.setAttribute("data-dragon-ai-sidebar-clearance", "true");
    }
    if (spacer.parentElement !== parent || parent.firstElementChild !== spacer) {
      parent.insertBefore(spacer, parent.firstChild);
    }
    spacer.style.cssText = "display:block;width:100%;height:" + height + "px;min-height:" + height + "px;flex:0 0 auto;order:-1;pointer-events:none;background:transparent;border:0;";
    bumpStickyStrip(strip, height);
    return spacer;
  }
  function pinFixedHost(host) {
    var roster = document.querySelector('[data-slot="bots-roster"]');
    var height = lockupHeight();
    var top = 0;
    var left = 0;
    var width = 256;
    var spacer = ensureClearance(height);
    if (spacer && spacer.getBoundingClientRect) {
      var box = spacer.getBoundingClientRect();
      top = Math.max(0, Math.round(box.top));
      left = Math.max(0, Math.round(box.left));
      if (box.width > 80) width = Math.max(256, Math.round(box.width));
      roster = null;
    }
    if (roster && roster.getBoundingClientRect) {
      var rail = roster.getBoundingClientRect();
      left = Math.max(0, Math.round(rail.left));
      if (rail.width > 80) width = Math.max(256, Math.round(rail.width));
    }
    host.setAttribute("data-dragon-ai-sidebar-fixed", "true");
    host.style.cssText = "position:fixed;z-index:40;top:" + top + "px;left:" + left + "px;width:" + width + "px;max-width:" + width + "px;min-width:" + width + "px;box-sizing:border-box;margin:0;padding:0;pointer-events:none;background:transparent;border:0;";
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
    return findColumnHost() || ensureInFlowHost() || ensureFixedHost();
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
    open.setAttribute("aria-expanded", "false");
    open.setAttribute("aria-label", LABEL);
    var backdrop = document.createElement("div");
    backdrop.setAttribute("data-dragon-ai-teams-backdrop", "true");
    backdrop.hidden = true;
    backdrop.setAttribute("hidden", "");
    var panel = document.createElement("div");
    panel.setAttribute("data-dragon-ai-teams-panel", "true");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-modal", "true");
    panel.setAttribute("aria-label", LABEL);
    panel.setAttribute("aria-hidden", "true");
    panel.hidden = true;
    panel.innerHTML = '<header><h2>Teams Marketplace</h2><p>Browse the GitHub catalog. Install a team to add its bots. Personal Assistant is already installed. Each team files under its own name, not Unassigned. Each seat shows a brief; hover or focus a seat for details. Recipe packs — no live logins.</p></header><div data-dragon-ai-teams-browse><div data-dragon-ai-teams-list></div></div><section data-dragon-ai-teams-detail hidden><button type="button" data-dragon-ai-teams-back>Back</button><h3 data-dragon-ai-teams-detail-title></h3><p data-dragon-ai-teams-detail-meta></p><p data-dragon-ai-teams-detail-blurb></p><p data-dragon-ai-teams-detail-body></p><p data-dragon-ai-teams-detail-connectors></p><ul data-dragon-ai-teams-detail-seats data-dragon-ai-team-seats></ul><button type="button" data-dragon-ai-teams-install data-dragon-ai-team-apply="true">Install</button></section><p data-dragon-ai-teams-status role="status"></p><div data-dragon-ai-teams-actions><button type="button" data-dragon-ai-teams-launch>Launch</button><button type="button" data-dragon-ai-teams-export>Export</button><label data-dragon-ai-teams-import-label>Import<input type="file" accept=".zip,.json,application/json,application/zip" data-dragon-ai-teams-import></label><button type="button" data-dragon-ai-teams-close>Close</button></div>';
    var catalog = [];
    var detailId = "";
    function setStatus(t) {
      var s = $("[data-dragon-ai-teams-status]", panel);
      if (s) s.textContent = t || "";
    }
    var hideTimer = 0;
    function reducedMotion() {
      try {
        return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
      } catch (e) {
        return false;
      }
    }
    function browseEl() { return $("[data-dragon-ai-teams-browse]", panel); }
    function detailEl() { return $("[data-dragon-ai-teams-detail]", panel); }
    function showBrowse() {
      var b = browseEl();
      var d = detailEl();
      if (b) { b.hidden = false; b.removeAttribute("hidden"); }
      if (d) { d.hidden = true; d.setAttribute("hidden", ""); }
      detailId = "";
    }
    function firstFocusable() {
      return $("[data-dragon-ai-team-row] [data-dragon-ai-team-apply]", panel)
        || $("[data-dragon-ai-teams-install]", panel)
        || $("[data-dragon-ai-teams-launch]", panel)
        || $("[data-dragon-ai-teams-close]", panel);
    }
    function show() {
      if (hideTimer) { clearTimeout(hideTimer); hideTimer = 0; }
      backdrop.hidden = false;
      backdrop.removeAttribute("hidden");
      panel.hidden = false;
      panel.removeAttribute("hidden");
      panel.setAttribute("aria-hidden", "false");
      open.setAttribute("aria-expanded", "true");
      showBrowse();
      load();
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          panel.setAttribute("data-dragon-ai-teams-visible", "true");
          var first = firstFocusable();
          if (first && first.focus) first.focus();
        });
      });
    }
    function hide() {
      panel.removeAttribute("data-dragon-ai-teams-visible");
      panel.setAttribute("aria-hidden", "true");
      open.setAttribute("aria-expanded", "false");
      if (hideTimer) clearTimeout(hideTimer);
      hideTimer = setTimeout(function () {
        hideTimer = 0;
        if (panel.getAttribute("data-dragon-ai-teams-visible") === "true") return;
        panel.hidden = true;
        panel.setAttribute("hidden", "");
        backdrop.hidden = true;
        backdrop.setAttribute("hidden", "");
        showBrowse();
        if (open && open.focus) open.focus();
      }, reducedMotion() ? 0 : 220);
    }
    function reloadRoster() {
      hide();
      try { location.reload(); } catch (e) {
        try { window.location.href = window.location.href; } catch (e2) {}
      }
    }
    function finishApply() { hide(); reloadRoster(); }
    function selectedIds() {
      return $all('input[type="checkbox"]:checked', panel).map(function (box) {
        return box.getAttribute("data-dragon-ai-team-id") || box.value;
      }).filter(Boolean);
    }
    function connectorText(team) {
      return (team.requiredConnectors || []).map(function (c) {
        return (c && c.displayName) || (c && c.id) || c;
      }).filter(Boolean).join(", ");
    }
    function findTeam(id) {
      return catalog.filter(function (t) { return t.id === id; })[0] || null;
    }
    function seatItem(team, bot, i) {
      var li = document.createElement("li");
      li.setAttribute("data-dragon-ai-seat-id", bot.id || "");
      var icon = document.createElement("img");
      icon.setAttribute("data-dragon-ai-seat-icon", "true");
      icon.setAttribute("aria-hidden", "true");
      icon.alt = "";
      var iconId = String(bot.id || "seat").replace(/[^a-z0-9-]/gi, "");
      icon.src = "./dragon-ai-branding/teams/" + (iconId || "seat") + ".svg";
      icon.addEventListener("error", function () {
        if (icon.dataset.fallback) return;
        icon.dataset.fallback = "1";
        icon.src = "./dragon-ai-branding/teams/seat.svg";
      });
      var copy = document.createElement("div");
      copy.setAttribute("data-dragon-ai-seat-copy", "true");
      var name = document.createElement("strong");
      name.textContent = bot.title || bot.id || "";
      var brief = document.createElement("span");
      brief.textContent = bot.description || "";
      copy.appendChild(name);
      copy.appendChild(brief);
      li.appendChild(icon);
      li.appendChild(copy);
      if (bot.descriptionDetail) {
        li.setAttribute("data-dragon-ai-seat-detail", "true");
        li.tabIndex = 0;
        var tipId = "dragon-seat-tip-" + (team.id || "team") + "-" + (bot.id || i);
        li.setAttribute("aria-describedby", tipId);
        var tip = document.createElement("div");
        tip.id = tipId;
        tip.setAttribute("role", "tooltip");
        tip.setAttribute("data-dragon-ai-seat-tooltip", "true");
        tip.textContent = bot.descriptionDetail;
        li.appendChild(tip);
      }
      return li;
    }
    function fillSeats(list, team) {
      list.textContent = "";
      (team.bots || []).forEach(function (bot, i) {
        list.appendChild(seatItem(team, bot, i));
      });
    }
    function showDetail(id) {
      var team = findTeam(id);
      if (!team) { setStatus("Pack not in catalog."); return; }
      detailId = id;
      var d = detailEl();
      var b = browseEl();
      if (b) { b.hidden = true; b.setAttribute("hidden", ""); }
      if (d) { d.hidden = false; d.removeAttribute("hidden"); }
      var title = $("[data-dragon-ai-teams-detail-title]", panel);
      var meta = $("[data-dragon-ai-teams-detail-meta]", panel);
      var blurb = $("[data-dragon-ai-teams-detail-blurb]", panel);
      var body = $("[data-dragon-ai-teams-detail-body]", panel);
      var cons = $("[data-dragon-ai-teams-detail-connectors]", panel);
      var seats = $("[data-dragon-ai-teams-detail-seats]", panel);
      if (title) title.textContent = team.displayName || team.name || id;
      if (meta) meta.textContent = (team.seats || team.botCount || 0) + " seats · " + (team.author || "Dragon AI");
      if (blurb) blurb.textContent = team.blurb || team.departmentJob || "";
      if (body) body.textContent = team.detail || team.blurb || "";
      if (cons) {
        cons.textContent = connectorText(team)
          ? ("Required connectors: " + connectorText(team))
          : "Required connectors: none listed";
      }
      if (seats) fillSeats(seats, team);
      setStatus("Review the pack, then Install, or go Back.");
    }
    function card(team) {
      var wrap = document.createElement("article");
      wrap.setAttribute("data-dragon-ai-team-id", team.id || "");
      wrap.setAttribute("data-dragon-ai-team-row", "true");
      var heading = document.createElement("div");
      heading.setAttribute("data-dragon-ai-team-heading", "true");
      var apply = document.createElement("button");
      apply.type = "button";
      apply.textContent = "Install";
      apply.setAttribute("data-dragon-ai-team-apply", "true");
      apply.setAttribute("data-dragon-ai-team-id", team.id || "");
      apply.setAttribute("aria-label", "Install " + (team.displayName || team.name || team.id || "team"));
      apply.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        installTeam(team.id);
      });
      var copy = document.createElement("span");
      copy.innerHTML = "<strong></strong><span></span><small></small><small></small>";
      copy.querySelector("strong").textContent = team.displayName || team.name || team.id;
      copy.querySelector("span").textContent = team.blurb || team.departmentJob || "";
      copy.querySelectorAll("small")[0].textContent =
        (team.seats || team.botCount || 0) + " seats · " + (team.author || "Dragon AI");
      copy.querySelectorAll("small")[1].textContent = connectorText(team);
      heading.appendChild(apply);
      heading.appendChild(copy);
      var details = document.createElement("button");
      details.type = "button";
      details.setAttribute("data-dragon-ai-teams-open-detail", "true");
      details.textContent = "Details";
      details.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        showDetail(team.id);
      });
      wrap.appendChild(heading);
      wrap.appendChild(details);
      var seats = document.createElement("ul");
      seats.setAttribute("data-dragon-ai-team-seats", "true");
      fillSeats(seats, team);
      if (seats.childNodes.length) wrap.appendChild(seats);
      return wrap;
    }
    function load() {
      setStatus("Loading marketplace…");
      fetch(API + "/api/marketplace").then(function (r) {
        if (!r.ok) throw new Error("marketplace");
        return r.json();
      }).catch(function () {
        return fetch(API + "/api/teams").then(function (r) { return r.json(); });
      }).then(function (data) {
        var list = $("[data-dragon-ai-teams-list]", panel);
        if (!list) return;
        list.textContent = "";
        catalog = data.teams || [];
        catalog.forEach(function (t) { list.appendChild(card(t)); });
        setStatus(catalog.length ? "Install a team to add its bots, or open Details." : "No teams listed.");
      }).catch(function () {
        setStatus("Teams Marketplace helper is not running on 127.0.0.1:8653.");
      });
    }
    function installTeam(id) {
      if (!id) { setStatus("Open Details, then Install."); return; }
      setStatus("Installing " + id + "…");
      fetch(API + "/api/marketplace/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: id })
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (data.error) { setStatus(data.message || data.error); return; }
        finishApply();
      }).catch(function () { setStatus("Install failed. Is the Teams Marketplace helper running?"); });
    }
    function installOne() {
      if (!detailId) { setStatus("Open Details, then Install."); return; }
      installTeam(detailId);
    }
    function launch() {
      var ids = selectedIds();
      if (!ids.length) { setStatus("Check one or more teams to launch."); return; }
      setStatus("Launching " + ids.length + " team" + (ids.length === 1 ? "" : "s") + "…");
      fetch(API + "/api/teams/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: ids })
      }).then(function (r) { return r.json(); }).then(function (data) {
        if (data.error) { setStatus(data.message || data.error); return; }
        finishApply();
      }).catch(function () { setStatus("Launch failed. Is the Teams Marketplace helper running?"); });
    }
    function exportSelected() {
      var ids = selectedIds();
      if (!ids.length) { setStatus("Check one or more teams to export."); return; }
      setStatus("Exporting…");
      fetch(API + "/api/teams/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: ids })
      }).then(function (r) {
        if (!r.ok) {
          return r.json().then(function (data) {
            throw new Error(data.message || data.error || "Export failed.");
          });
        }
        var name = "dragon-teams.zip";
        var header = r.headers.get("Content-Disposition") || "";
        var match = /filename="?([^"]+)"?/.exec(header);
        if (match) name = match[1];
        return r.blob().then(function (blob) { return { blob: blob, name: name }; });
      }).then(function (out) {
        var a = document.createElement("a");
        a.href = URL.createObjectURL(out.blob);
        a.download = out.name;
        document.body.appendChild(a);
        a.click();
        a.remove();
        setStatus("Exported " + out.name + " (catalog-ready; secrets stripped).");
      }).catch(function (err) {
        setStatus(err && err.message ? err.message : "Export failed.");
      });
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
    backdrop.addEventListener("click", hide);
    $("[data-dragon-ai-teams-close]", panel).addEventListener("click", hide);
    $("[data-dragon-ai-teams-launch]", panel).addEventListener("click", launch);
    $("[data-dragon-ai-teams-export]", panel).addEventListener("click", exportSelected);
    var back = $("[data-dragon-ai-teams-back]", panel);
    if (back) {
      back.addEventListener("click", function () {
        showBrowse();
        setStatus("Install a team to add its bots, or open Details.");
      });
    }
    var inst = $("[data-dragon-ai-teams-install]", panel);
    if (inst) inst.addEventListener("click", installOne);
    var inp = $("[data-dragon-ai-teams-import]", panel);
    if (inp) inp.addEventListener("change", function () { importFile(inp.files && inp.files[0]); });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && !panel.hidden) hide();
    });
    root.appendChild(open);
    if (document.body) {
      document.body.appendChild(backdrop);
      document.body.appendChild(panel);
    } else {
      root.appendChild(backdrop);
      root.appendChild(panel);
    }
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
