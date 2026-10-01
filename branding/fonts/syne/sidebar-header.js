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
