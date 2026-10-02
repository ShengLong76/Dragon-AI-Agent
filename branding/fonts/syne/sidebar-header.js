(function () {
  // Expected DOM order: lockup → Teams Marketplace → Sessions/Bots
  // Lockup sits to the right of hide-sidebar (1.75× the prior 32px mark).
  var TITLE = "Dragon AI";
  var ACCESSIBLE = "Dragon AI Agent";
  var LOGO = "./dragon-ai-branding/dragon-ai-agent-logo.svg";
  var LOGO_PX = 56;
  var LOCKUP_STYLE = "display:flex;align-items:center;gap:8px;box-sizing:border-box;padding:0 0 8px;margin:0 0 4px;flex:0 0 auto;position:relative;z-index:2;isolation:isolate;color:inherit;background:transparent;background-color:transparent;border:0;border-width:0;border-style:none;outline:none;box-shadow:none;";
  var LOCKUP_AFTER_HIDE_STYLE = "display:flex;align-items:center;gap:8px;box-sizing:border-box;padding:0;margin:0 0 0 8px;flex:0 0 auto;position:relative;z-index:2;isolation:isolate;color:inherit;background:transparent;background-color:transparent;border:0;border-width:0;border-style:none;outline:none;box-shadow:none;pointer-events:auto;";
  var LOGO_STYLE = "display:block;height:56px;width:56px;max-width:56px;max-height:56px;border:0;border-width:0;border-style:none;outline:none;box-shadow:none;background:transparent;padding:0;margin:0;border-radius:0;position:relative;z-index:2;flex:0 0 56px;";
  var CHROME_STYLE = "display:flex;flex-direction:column;align-items:stretch;width:100%;min-height:96px;box-sizing:border-box;margin:0;padding:0;flex:0 0 auto;order:-1;position:relative;z-index:1;pointer-events:auto;background:transparent;border:0;";
  function pinLogo(img) {
    img.src = LOGO;
    img.alt = "";
    img.setAttribute("aria-hidden", "true");
    img.setAttribute("data-dragon-ai-sidebar-logo", "true");
    img.style.cssText = LOGO_STYLE;
    img.removeAttribute("width");
    img.removeAttribute("height");
  }
  function pinWrap(wrap, afterHide) {
    wrap.setAttribute("data-dragon-ai-sidebar-brand", "true");
    wrap.setAttribute("role", "img");
    wrap.setAttribute("aria-label", ACCESSIBLE);
    wrap.setAttribute("data-dragon-ai-lockup-after-hide", afterHide ? "true" : "false");
    wrap.style.cssText = afterHide ? LOCKUP_AFTER_HIDE_STYLE : LOCKUP_STYLE;
  }
  function accessibleName(el) {
    return (
      (el.getAttribute && (el.getAttribute("aria-label") || el.getAttribute("title")))
      || labelOf(el)
    ).replace(/\s+/g, " ").trim();
  }
  function isHideSidebar(el) {
    if (!el || !el.getAttribute) return false;
    if (el.getAttribute("data-dragon-ai-sidebar-brand") === "true") return false;
    if (el.getAttribute("data-sidebar") === "rail") return false;
    if (el.getAttribute("data-sidebar") === "trigger") return true;
    if (el.getAttribute("data-slot") === "sidebar-trigger") return true;
    var action = el.getAttribute("data-action-id") || el.getAttribute("data-action");
    if (action === "view.toggleSidebar") return true;
    if (el.getAttribute("data-dragon-ai-hide-sidebar") === "true") return true;
    var name = accessibleName(el);
    if (/^(hide|show) sidebar$/i.test(name)) return true;
    if (/toggle (sessions )?sidebar/i.test(name)) return true;
    if (/(hide|show|toggle).{0,20}sidebar/i.test(name) && !/right|file browser|swap/i.test(name)) return true;
    return false;
  }
  function pinHide(el) {
    el.setAttribute("data-dragon-ai-hide-sidebar", "true");
    return el;
  }
  function findHideSidebar() {
    var marked = document.querySelector("[data-dragon-ai-hide-sidebar='true']");
    if (marked && marked.isConnected && isHideSidebar(marked)) return marked;
    var sel = document.querySelector(
      '[data-sidebar="trigger"], [data-slot="sidebar-trigger"], [data-action-id="view.toggleSidebar"], [data-action="view.toggleSidebar"], [aria-label="Hide sidebar"], [aria-label="Show sidebar"]'
    );
    if (sel && isHideSidebar(sel)) return pinHide(sel);
    var nodes = document.querySelectorAll("button, [role='button'], a");
    var i;
    for (i = 0; i < nodes.length; i++) {
      if (isHideSidebar(nodes[i])) return pinHide(nodes[i]);
    }
    return null;
  }
  function placeBrand(wrap) {
    var hide = findHideSidebar();
    if (hide && hide.parentNode) {
      if (wrap.previousElementSibling !== hide) {
        hide.parentNode.insertBefore(wrap, hide.nextSibling);
      }
      pinWrap(wrap, true);
      return true;
    }
    pinWrap(wrap, false);
    return false;
  }
  function syncChromePad() {
    var brand = document.querySelector("[data-dragon-ai-sidebar-brand]");
    var chrome = document.querySelector("[data-dragon-ai-sidebar-chrome]")
      || document.querySelector("[data-dragon-ai-sidebar-row]");
    if (!chrome) return;
    if (!brand || chrome.contains(brand)) {
      chrome.style.paddingTop = "";
      return;
    }
    try {
      var box = brand.getBoundingClientRect();
      var host = chrome.getBoundingClientRect();
      var need = Math.max(0, Math.ceil(box.bottom + 12 - host.top));
      chrome.style.paddingTop = need ? need + "px" : "";
    } catch (e) {}
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
  function closestRow(el) {
    var node = el;
    while (node && node.getAttribute) {
      if (node.getAttribute("data-dragon-ai-sidebar-row") === "true") return node;
      node = node.parentNode;
    }
    return null;
  }
  function ensureRow(host) {
    var row = document.querySelector("[data-dragon-ai-sidebar-row]");
    if (!row) {
      row = document.createElement("div");
      row.setAttribute("data-dragon-ai-sidebar-row", "true");
      row.style.pointerEvents = "auto";
    }
    if (row.parentElement !== host) {
      host.insertBefore(row, host.firstChild);
    }
    return row;
  }
  function mount() {
    var host = findDragonSidebarHost();
    if (!host) return;
    var row = ensureRow(host);
    var existing = document.querySelector("[data-dragon-ai-sidebar-brand]");
    if (existing) {
      var old = existing.querySelector("img");
      if (old) pinLogo(old);
      if (!placeBrand(existing) && existing.parentNode !== row) {
        row.insertBefore(existing, row.firstChild);
      }
      syncChromePad();
      if (host.getAttribute("data-dragon-ai-sidebar-fixed")) pinFixedHost(host);
      return;
    }
    var wrap = document.createElement("div");
    pinWrap(wrap, false);
    var img = document.createElement("img");
    pinLogo(img);
    var span = document.createElement("span");
    span.setAttribute("aria-hidden", "true");
    span.textContent = TITLE;
    wrap.appendChild(img);
    wrap.appendChild(span);
    row.appendChild(wrap);
    placeBrand(wrap);
    syncChromePad();
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
