(function () {
  var TITLE = "Dragon AI";
  var ACCESSIBLE = "Dragon AI Agent";
  var LOGO = "./dragon-ai-branding/dragon-ai-agent-logo.svg";
  var LOCKUP_STYLE = "display:flex;align-items:center;gap:8px;box-sizing:border-box;padding:0;margin:0;color:inherit;background:transparent;background-color:transparent;border:0;border-width:0;border-style:none;outline:none;box-shadow:none;";
  var LOGO_STYLE = "display:block;height:32px;width:32px;max-width:32px;max-height:32px;border:0;border-width:0;border-style:none;outline:none;box-shadow:none;background:transparent;padding:0;margin:0;border-radius:0;";
  function pinLogo(img) {
    img.src = LOGO;
    img.alt = "";
    img.setAttribute("aria-hidden", "true");
    img.setAttribute("data-dragon-ai-sidebar-logo", "true");
    img.style.cssText = LOGO_STYLE;
    img.removeAttribute("width");
    img.removeAttribute("height");
  }
  function pinWrap(wrap) {
    wrap.setAttribute("data-dragon-ai-sidebar-brand", "true");
    wrap.setAttribute("role", "img");
    wrap.setAttribute("aria-label", ACCESSIBLE);
    wrap.style.cssText = LOCKUP_STYLE;
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
        var t = labelOf(kids[i]);
        if (/^bots$/i.test(t)) bots += 1;
        if (/^sessions$/i.test(t)) sessions += 1;
      }
      if (bots && sessions) return parent;
      node = parent;
      hops += 1;
    }
    return tab.parentElement || tab;
  }
  function lockupHeight() {
    var row = document.querySelector("[data-dragon-ai-sidebar-row]");
    if (row && row.getBoundingClientRect) {
      var height = row.getBoundingClientRect().height;
      if (height > 24) return Math.max(96, Math.ceil(height + 8));
    }
    return 96;
  }
  function ensureClearance(strip, height) {
    var parent = strip && strip.parentElement;
    if (!parent) return null;
    var spacer = document.querySelector("[data-dragon-ai-sidebar-clearance]");
    if (!spacer) {
      spacer = document.createElement("div");
      spacer.setAttribute("data-dragon-ai-sidebar-clearance", "true");
    }
    if (spacer.parentElement !== parent || spacer.nextSibling !== strip) {
      parent.insertBefore(spacer, strip);
    }
    spacer.style.cssText = "display:block;width:100%;height:" + height + "px;min-height:" + height + "px;flex:0 0 " + height + "px;pointer-events:none;background:transparent;border:0;";
    return spacer;
  }
  function pinFixedHost(host) {
    var tab = findBotsTab();
    var strip = tab ? findTabStrip(tab) : null;
    var roster = document.querySelector('[data-slot="bots-roster"]');
    var height = lockupHeight();
    var top = 96;
    var left = 0;
    var width = 256;
    if (strip) {
      var spacer = ensureClearance(strip, height);
      if (spacer && spacer.getBoundingClientRect) {
        var box = spacer.getBoundingClientRect();
        top = Math.max(0, Math.round(box.top));
        left = Math.max(0, Math.round(box.left));
        if (box.width > 80) width = Math.round(box.width);
        roster = null;
      }
    }
    if (roster && roster.getBoundingClientRect) {
      var rail = roster.getBoundingClientRect();
      left = Math.max(0, Math.round(rail.left));
      if (rail.width > 80) width = Math.round(rail.width);
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
    return findColumnHost() || ensureFixedHost();
  }
  function closestRow(el) {
    var node = el;
    while (node && node.getAttribute) {
      if (node.getAttribute("data-dragon-ai-sidebar-row") === "true") return node;
      node = node.parentNode;
    }
    return el;
  }
  function mount() {
    var host = findDragonSidebarHost();
    if (!host) return;
    var existing = document.querySelector("[data-dragon-ai-sidebar-brand]");
    if (existing) {
      var oldRow = closestRow(existing);
      if (oldRow && !host.contains(oldRow)) {
        host.insertBefore(oldRow, host.firstChild);
      }
      pinWrap(existing);
      var old = existing.querySelector("img");
      if (old) pinLogo(old);
      if (host.getAttribute("data-dragon-ai-sidebar-fixed")) pinFixedHost(host);
      return;
    }
    var row = document.createElement("div");
    row.setAttribute("data-dragon-ai-sidebar-row", "true");
    row.style.pointerEvents = "auto";
    var wrap = document.createElement("div");
    pinWrap(wrap);
    var img = document.createElement("img");
    pinLogo(img);
    var span = document.createElement("span");
    span.setAttribute("aria-hidden", "true");
    span.textContent = TITLE;
    wrap.appendChild(img);
    wrap.appendChild(span);
    row.appendChild(wrap);
    host.insertBefore(row, host.firstChild);
    if (host.getAttribute("data-dragon-ai-sidebar-fixed")) pinFixedHost(host);
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
