(function () {
  // First-run in-app Models / provider connect. Copy only — keep CLI names
  // (`hermes model`) and binary/token strings intact.
  var MARK = "data-dragon-ai-provider-setup";
  var OTHER = "data-dragon-ai-other-providers";
  var OTHER_LABEL = "Other providers";
  var INHERIT_URL = "http://127.0.0.1:8655/api/inherit-models";
  var PROTECTED = /hermes\s+model|hermes\s+auth|hermes\s+setup|hermes\.exe|hermes-airmaze|x-hermes-session-token|hermes:\/\/|~\/\.hermes/i;
  var sawProviderUi = false;
  var sawDisconnected = false;
  var inheritTimer = 0;
  var lastInherit = 0;

  function labelOf(el) {
    return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
  }

  function looksLikeProviderUi(text) {
    return /let'?s get you setup|connect a model provider|other providers|nous portal|run models locally|i'?ll choose a provider later/i.test(text || "") || (text || "").indexOf(OTHER_LABEL) !== -1;
  }

  function findProviderRoot() {
    var nodes = document.querySelectorAll('[role="dialog"], [data-state="open"], [data-radix-dialog-content], [class*="modal"], [class*="dialog"]');
    var i;
    for (i = 0; i < nodes.length; i++) {
      if (looksLikeProviderUi(labelOf(nodes[i]))) return nodes[i];
    }
    var all = document.querySelectorAll("h1, h2, [class*='title']");
    for (i = 0; i < all.length; i++) {
      if (/let'?s get you setup/i.test(labelOf(all[i]))) {
        return all[i].closest('[role="dialog"]') || all[i].closest('[data-state]') || all[i].parentElement;
      }
    }
    return null;
  }

  function rewriteText(raw) {
    var text = String(raw || "");
    if (!/hermes/i.test(text)) return text;
    if (PROTECTED.test(text) && !/hermes is not connected|recommended way to run hermes|setup with hermes|run hermes\b/i.test(text)) {
      return text;
    }
    return text
      .replace(/Hermes Agent/g, "Dragon AI Agent")
      .replace(/Hermes Desktop/g, "Dragon AI Agent")
      .replace(/Hermes is not connected/g, "Dragon AI is not connected")
      .replace(/the recommended way to run Hermes/g, "the recommended way to run Dragon AI")
      .replace(/\brun Hermes\b/g, "run Dragon AI")
      .replace(/\bHermes\b/g, function (match, offset, full) {
        var window = full.slice(Math.max(0, offset - 2), offset + 18);
        if (/`hermes|hermes model|hermes auth|hermes setup|hermes\.exe/i.test(window)) {
          return match;
        }
        return "Dragon AI";
      });
  }

  function walkText(root) {
    if (!root) return;
    var skip = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, CODE: 1, PRE: 1, KBD: 1 };
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        var parent = node.parentElement;
        if (!parent || skip[parent.tagName]) return NodeFilter.FILTER_REJECT;
        if (!node.nodeValue || !/hermes/i.test(node.nodeValue)) return NodeFilter.FILTER_SKIP;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var node;
    while ((node = walker.nextNode())) {
      var next = rewriteText(node.nodeValue);
      if (next !== node.nodeValue) node.nodeValue = next;
    }
  }

  function expandOther(root) {
    if (!root) return;
    var details = root.querySelectorAll("details");
    var i;
    for (i = 0; i < details.length; i++) {
      if (/other providers/i.test(labelOf(details[i])) || labelOf(details[i]).indexOf(OTHER_LABEL) !== -1) {
        details[i].open = true;
        details[i].setAttribute(OTHER, "1");
      }
    }
    var buttons = root.querySelectorAll("button, [role='button'], [aria-expanded], summary");
    for (i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      if (!/other providers/i.test(labelOf(b)) && labelOf(b).indexOf(OTHER_LABEL) === -1) continue;
      b.setAttribute(OTHER, "1");
      if (b.getAttribute("aria-expanded") !== "true") {
        try { b.click(); } catch (e) {}
      }
    }
  }

  function looksDisconnected(text) {
    return /not connected to any AI provider|i'?ll choose a provider later|let'?s get you setup/i.test(text || "");
  }

  function notifyInherit() {
    var now = Date.now();
    if (now - lastInherit < 1500) return;
    lastInherit = now;
    try {
      fetch(INHERIT_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(function () {});
    } catch (e) {}
  }

  function scheduleInherit() {
    if (inheritTimer) clearTimeout(inheritTimer);
    inheritTimer = setTimeout(notifyInherit, 800);
  }

  function bindProviderClicks(root) {
    if (!root || root.getAttribute("data-dragon-ai-inherit-bound") === "1") return;
    root.setAttribute("data-dragon-ai-inherit-bound", "1");
    root.addEventListener("click", function (ev) {
      var t = ev.target;
      var label = "";
      while (t && t !== root) {
        label = labelOf(t);
        if (/nous portal|run models locally|openrouter|openai|anthropic|gemini|grok|self-hosted|ollama|custom/i.test(label)) {
          scheduleInherit();
          return;
        }
        t = t.parentElement;
      }
    }, true);
  }

  function polish(root) {
    if (!root) return;
    root.setAttribute(MARK, "1");
    walkText(root);
    expandOther(root);
    bindProviderClicks(root);
  }

  function tick() {
    try {
      var root = findProviderRoot();
      if (root) {
        sawProviderUi = true;
        polish(root);
      } else if (sawProviderUi) {
        scheduleInherit();
      }
      walkText(document.body);
      var bodyText = document.body ? labelOf(document.body) : "";
      if (looksDisconnected(bodyText)) sawDisconnected = true;
      else if (sawDisconnected && sawProviderUi) scheduleInherit();
    } catch (e) {}
  }

  function start() {
    tick();
    var obs = new MutationObserver(function () { tick(); });
    if (document.body) {
      obs.observe(document.body, { childList: true, subtree: true, characterData: true });
    }
    setInterval(tick, 1500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
