(function () {
  // Product workspace after Begin (every install):
  // default Bots tab; right pane is the bot VM screen, not a Hermes file tree.
  // Sessions / Bots stay below the Dragon logo and Teams Marketplace.
  var MARK = "data-dragon-ai-bot-workspace";
  var HIDDEN_TREE = "data-dragon-ai-hidden-file-tree";
  var HIDDEN_TOAST = "data-dragon-ai-hidden-hermes-toast";
  var HIDDEN_LINUX = "data-dragon-ai-hidden-embedded-linux";
  var SCREEN_MARK = "data-dragon-ai-bot-vm-screen";
  var TREE_HINT = /hermes_cli|ocp_adapter|playeright|dockerfile|third_party|contributors|gateway\.py/i;
  var TOAST_TEXT = /couldn'?t finish (this|the) reply|run hermes setup|hermes couldn'?t finish|something went wrong while hermes/i;
  var SCREEN_LABEL = /^(start )?screen$|^bot screen$|^take over$|^hand back$|^live preview$/i;
  var FILE_BROWSER_LABEL = /file browser|hide file browser|close (file )?browser|explorer/i;
  var EMBEDDED_LINUX = "Embedded Linux";
  var FINISH_REPLY = "couldn't finish the reply";
  var openedBots = false;
  var openedScreen = false;
  var lastToastSweep = 0;

  function labelOf(el) {
    return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
  }

  function accessibleName(el) {
    if (!el || !el.getAttribute) return "";
    return (
      el.getAttribute("aria-label") ||
      el.getAttribute("title") ||
      labelOf(el)
    ).replace(/\s+/g, " ").trim();
  }

  function stillOnboarding() {
    try {
      var text = document.body ? (document.body.innerText || document.body.textContent || "") : "";
      if (/let'?s get you setup|connect a model provider/i.test(text)) return true;
      if (/xai grok oauth|supergrok/i.test(text) && /connected/i.test(text) && /\bbegin\b/i.test(text)) return true;
      if (/default model/i.test(text) && /\bbegin\b/i.test(text) && /\bchange\b/i.test(text)) return true;
      return false;
    } catch (e) {
      return false;
    }
  }

  function findBotsTab() {
    var tabs = document.querySelectorAll('[role="tab"], button, a, [role="tablist"] *');
    var i;
    for (i = 0; i < tabs.length; i++) {
      if (/^bots$/i.test(labelOf(tabs[i]))) return tabs[i];
    }
    return null;
  }

  function isSelected(el) {
    if (!el) return false;
    var aria = el.getAttribute && el.getAttribute("aria-selected");
    if (aria === "true") return true;
    var pressed = el.getAttribute && el.getAttribute("aria-pressed");
    if (pressed === "true") return true;
    var cls = (el.className && el.className.baseVal != null) ? String(el.className.baseVal) : String(el.className || "");
    return /\b(active|selected|current)\b/i.test(cls);
  }

  function openBotsTab() {
    if (openedBots || stillOnboarding()) return;
    var tab = findBotsTab();
    if (!tab) return;
    if (!isSelected(tab)) {
      try { tab.click(); } catch (e) {}
    }
    openedBots = true;
    tab.setAttribute(MARK, "bots");
  }

  function looksLikeFileTree(el) {
    if (!el) return false;
    var text = labelOf(el);
    if (text.length < 12 || text.length > 4000) return false;
    var hits = 0;
    if (/hermes_cli/i.test(text)) hits += 1;
    if (/dockerfile/i.test(text)) hits += 1;
    if (/ocp_adapter|playeright|third_party/i.test(text)) hits += 1;
    if (/\bHERMES\b/.test(text) && TREE_HINT.test(text)) hits += 1;
    return hits >= 2;
  }

  function hideNode(el, mark) {
    if (!el || el === document.body || el === document.documentElement) return;
    el.setAttribute(mark, "1");
    el.style.display = "none";
  }

  function hideFileTree() {
    var nodes = document.querySelectorAll(
      '[data-slot*="file"], [class*="file-tree"], [class*="filetree"], [class*="explorer"], [class*="file-browser"], aside, [role="complementary"], [data-panel], [data-side="right"]'
    );
    var i;
    for (i = 0; i < nodes.length; i++) {
      if (looksLikeFileTree(nodes[i])) hideNode(nodes[i], HIDDEN_TREE);
    }
    var headers = document.querySelectorAll("h1, h2, h3, [class*='title'], [class*='header']");
    for (i = 0; i < headers.length; i++) {
      if (!/^hermes$/i.test(labelOf(headers[i]))) continue;
      var pane = headers[i].closest("aside, [role='complementary'], [data-panel], [data-side='right']") || headers[i].parentElement;
      if (pane && (looksLikeFileTree(pane) || TREE_HINT.test(labelOf(pane)))) {
        hideNode(pane, HIDDEN_TREE);
      }
    }
    var buttons = document.querySelectorAll("button, [role='button'], [aria-expanded='true']");
    for (i = 0; i < buttons.length; i++) {
      var name = accessibleName(buttons[i]);
      if (!FILE_BROWSER_LABEL.test(name)) continue;
      if (buttons[i].getAttribute("aria-expanded") === "true") {
        try { buttons[i].click(); } catch (e) {}
      }
    }
  }

  function openBotVmScreen() {
    if (openedScreen || stillOnboarding()) return;
    var nodes = document.querySelectorAll("button, a, [role='button'], [role='tab']");
    var i;
    for (i = 0; i < nodes.length; i++) {
      var name = accessibleName(nodes[i]);
      if (!SCREEN_LABEL.test(name)) continue;
      if (isSelected(nodes[i])) {
        openedScreen = true;
        nodes[i].setAttribute(SCREEN_MARK, "1");
        return;
      }
      try { nodes[i].click(); } catch (e) {}
      openedScreen = true;
      nodes[i].setAttribute(SCREEN_MARK, "1");
      return;
    }
    var display = document.querySelector("canvas, [data-slot*='screen'], [data-slot*='display'], video");
    if (display) {
      display.setAttribute(SCREEN_MARK, "1");
      openedScreen = true;
    }
  }

  function hideHermesToasts() {
    var now = Date.now();
    if (now - lastToastSweep < 400) return;
    lastToastSweep = now;
    var nodes = document.querySelectorAll('[role="alert"], [class*="toast"], [class*="sonner"], [data-sonner-toast], [class*="error"], li, p, div');
    var i;
    for (i = 0; i < nodes.length; i++) {
      var text = labelOf(nodes[i]);
      if (!TOAST_TEXT.test(text) && text.indexOf(FINISH_REPLY) === -1) continue;
      if (text.length > 360) continue;
      hideNode(nodes[i], HIDDEN_TOAST);
      var parent = nodes[i].parentElement;
      if (parent && parent !== document.body && TOAST_TEXT.test(labelOf(parent)) && labelOf(parent).length < 420) {
        hideNode(parent, HIDDEN_TOAST);
      }
    }
  }

  function hideEmbeddedLinux() {
    var nodes = document.querySelectorAll("button, span, div, p, [role='button'], [class*='connection'], [class*='gateway']");
    var i;
    for (i = 0; i < nodes.length; i++) {
      var text = labelOf(nodes[i]);
      if (text !== EMBEDDED_LINUX && !/^embedded linux$/i.test(text)) continue;
      hideNode(nodes[i], HIDDEN_LINUX);
    }
  }

  function tick() {
    try {
      if (stillOnboarding()) return;
      openBotsTab();
      hideFileTree();
      hideHermesToasts();
      hideEmbeddedLinux();
      openBotVmScreen();
    } catch (e) {}
  }

  function start() {
    tick();
    if (document.body) {
      try {
        new MutationObserver(function () { tick(); }).observe(document.body, {
          childList: true,
          subtree: true,
          characterData: true
        });
      } catch (e) {}
    }
    setInterval(tick, 1500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
