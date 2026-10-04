(function () {
  // First-run in-app provider connect. This dialog is the install first screen.
  // Starts expanded; recommends xAI Grok (not Nous Portal).
  // After a successful connect, keep the confirmation: DEFAULT MODEL, grok-4.7,
  // Change, and [ BEGIN ]. Do not return to the provider list.
  // Copy only - keep CLI names (`hermes model`) and binary/token strings intact.
  var MARK = "data-dragon-ai-provider-setup";
  var CONNECTED_MARK = "data-dragon-ai-provider-connected";
  var OTHER = "data-dragon-ai-other-providers";
  var OTHER_LABEL = "Other providers";
  var RECOMMENDED = "data-dragon-ai-recommended";
  var HIDDEN_ERR = "data-dragon-ai-hidden-setup-error";
  var HIDDEN_LIST = "data-dragon-ai-hidden-provider-list";
  var INHERIT_URL = "http://127.0.0.1:8655/api/inherit-models";
  var PROTECTED = /hermes\s+model|hermes\s+auth|hermes\s+setup|hermes\.exe|hermes-airmaze|x-hermes-session-token|hermes:\/\/|~\/\.hermes/i;
  var EXPAND_LABEL = /other providers|i'?ll choose a provider later|show (all|more)|more providers|all providers/i;
  var ERROR_TEXT = /errno\s*-?\s*2|name or service not known|setup\.status|runtime resolution still failed/i;
  var PROVIDER_ROW = /nous portal|run models locally|openrouter|openai|anthropic|gemini|grok|self-hosted|ollama|custom|fireworks|minimax|opencode|chatgpt|codex/i;
  var LIST_ROW = /nous portal|run models locally|fireworks|chatgpt or codex|minimax|opencode|anthropic api|anthropic oauth|i'?ll choose a provider later|other providers/i;
  var sawProviderUi = false;
  var sawConnected = false;
  var sawDisconnected = false;
  var inheritTimer = 0;
  var lastInherit = 0;

  function labelOf(el) {
    return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
  }

  function looksLikeConnectedConfirm(text) {
    text = text || "";
    var oauth = /xai grok oauth|supergrok|premium\+|grok oauth/i.test(text) && /connected/i.test(text);
    var begin = /default model/i.test(text) && /\bbegin\b/i.test(text);
    return oauth || begin;
  }

  function looksLikeProviderUi(text) {
    if (looksLikeConnectedConfirm(text)) return false;
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
    if (!/hermes/i.test(text) && !/recommended way to run/i.test(text)) return text;
    if (PROTECTED.test(text) && !/hermes is not connected|recommended way to run hermes|setup with hermes|run hermes\b|hermes connects automatically/i.test(text)) {
      return text;
    }
    return text
      .replace(/Hermes Agent/g, "Dragon AI Agent")
      .replace(/Hermes Desktop/g, "Dragon AI Agent")
      .replace(/Hermes is not connected/g, "Dragon AI is not connected")
      .replace(/Hermes connects automatically/g, "Dragon AI connects automatically")
      .replace(/hermes connects automatically/gi, "Dragon AI connects automatically")
      .replace(/\s*[—–-]\s*the recommended way to run (?:Hermes|Dragon AI)/gi, "")
      .replace(/the recommended way to run (?:Hermes|Dragon AI)/gi, "one subscription for 300+ frontier models")
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
        if (!node.nodeValue) return NodeFilter.FILTER_SKIP;
        if (!/hermes|recommended way to run/i.test(node.nodeValue)) return NodeFilter.FILTER_SKIP;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var node;
    while ((node = walker.nextNode())) {
      var next = rewriteText(node.nodeValue);
      if (next !== node.nodeValue) node.nodeValue = next;
    }
  }

  function isExpandControl(el) {
    var text = labelOf(el);
    if (EXPAND_LABEL.test(text) || text.indexOf(OTHER_LABEL) !== -1) return true;
    if (el.tagName === "SUMMARY") return true;
    if (el.getAttribute("aria-expanded") === "false" && text.length < 4) return true;
    return false;
  }

  function expandAll(root) {
    if (!root) return;
    var details = root.querySelectorAll("details");
    var i;
    for (i = 0; i < details.length; i++) {
      details[i].open = true;
      if (EXPAND_LABEL.test(labelOf(details[i])) || labelOf(details[i]).indexOf(OTHER_LABEL) !== -1) {
        details[i].setAttribute(OTHER, "1");
      }
    }
    var buttons = root.querySelectorAll("button, [role='button'], [aria-expanded], summary");
    for (i = 0; i < buttons.length; i++) {
      var b = buttons[i];
      if (!isExpandControl(b)) continue;
      if (EXPAND_LABEL.test(labelOf(b)) || labelOf(b).indexOf(OTHER_LABEL) !== -1) {
        b.setAttribute(OTHER, "1");
      }
      if (b.getAttribute("aria-expanded") === "false") {
        try { b.click(); } catch (e) {}
        b.setAttribute("aria-expanded", "true");
      }
    }
  }

  function hideSetupError(root) {
    if (!root) return;
    var nodes = root.querySelectorAll('[role="alert"], [class*="error"], [class*="banner"], [class*="toast"], p, div, span');
    var i;
    for (i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var text = labelOf(el);
      if (!ERROR_TEXT.test(text)) continue;
      if (text.length > 280) continue;
      el.setAttribute(HIDDEN_ERR, "1");
      el.style.display = "none";
      var parent = el.parentElement;
      if (parent && parent !== root && labelOf(parent).length < 320 && ERROR_TEXT.test(labelOf(parent))) {
        parent.setAttribute(HIDDEN_ERR, "1");
        parent.style.display = "none";
      }
    }
  }

  function smallestMatching(root, pattern) {
    var nodes = root.querySelectorAll("button, a, [role='button'], li, [class*='item'], [class*='row'], [class*='card'], div");
    var best = null;
    var bestLen = 0;
    var i;
    for (i = 0; i < nodes.length; i++) {
      var text = labelOf(nodes[i]);
      if (!pattern.test(text)) continue;
      if (!best || text.length < bestLen) {
        best = nodes[i];
        bestLen = text.length;
      }
    }
    return best;
  }

  function hideRecommendedBadges(row) {
    if (!row) return;
    var nodes = row.querySelectorAll("span, small, [class*='badge'], [class*='pill'], [class*='tag']");
    var i;
    for (i = 0; i < nodes.length; i++) {
      var text = labelOf(nodes[i]);
      if (/^recommended$/i.test(text) || (text.length < 16 && /recommended/i.test(text))) {
        nodes[i].setAttribute("data-dragon-ai-nous-recommended", "0");
        nodes[i].style.display = "none";
      }
    }
    row.removeAttribute("data-recommended");
    row.setAttribute("data-dragon-ai-not-recommended", "1");
  }

  function recommendGrok(root) {
    if (!root) return;
    var nous = smallestMatching(root, /nous portal/i);
    var grok = smallestMatching(root, /xai\s*grok|^grok\b|xai grok/i);
    if (nous) hideRecommendedBadges(nous);
    var badges = root.querySelectorAll("span, small, [class*='badge'], [class*='pill'], [class*='tag']");
    var i;
    for (i = 0; i < badges.length; i++) {
      var text = labelOf(badges[i]);
      if (!/^recommended$/i.test(text) && !(text.length < 16 && /recommended/i.test(text))) continue;
      if (grok && grok.contains(badges[i])) continue;
      badges[i].setAttribute("data-dragon-ai-nous-recommended", "0");
      badges[i].style.display = "none";
    }
    if (!grok) return;
    grok.setAttribute(RECOMMENDED, "1");
    if (!grok.querySelector("[data-dragon-ai-recommended-badge]")) {
      var badge = document.createElement("span");
      badge.setAttribute("data-dragon-ai-recommended-badge", "1");
      badge.textContent = "Recommended";
      grok.appendChild(badge);
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
        if (PROVIDER_ROW.test(label)) {
          scheduleInherit();
          return;
        }
        t = t.parentElement;
      }
    }, true);
  }

  function hideProviderList(root) {
    if (!root) return;
    var dialogs = document.querySelectorAll('[role="dialog"], [data-state="open"], [data-radix-dialog-content], [class*="modal"], [class*="dialog"]');
    var i;
    for (i = 0; i < dialogs.length; i++) {
      var dialogText = labelOf(dialogs[i]);
      if (looksLikeProviderUi(dialogText) && !looksLikeConnectedConfirm(dialogText)) {
        dialogs[i].setAttribute(HIDDEN_LIST, "1");
        dialogs[i].style.display = "none";
      }
    }
    var rows = root.querySelectorAll("button, a, [role='button'], li, [class*='item'], [class*='row'], [class*='card']");
    for (i = 0; i < rows.length; i++) {
      var text = labelOf(rows[i]);
      if (!LIST_ROW.test(text)) continue;
      if (/default model|\bbegin\b|change|xai grok oauth|supergrok/i.test(text)) continue;
      if (text.length > 240) continue;
      rows[i].setAttribute(HIDDEN_LIST, "1");
      rows[i].style.display = "none";
    }
  }

  function polishConnected(root) {
    if (!root) return;
    root.setAttribute(CONNECTED_MARK, "1");
    walkText(root);
    hideSetupError(root);
    hideProviderList(root);
    scheduleInherit();
  }

  function polish(root) {
    if (!root) return;
    if (sawConnected || looksLikeConnectedConfirm(labelOf(root))) {
      sawConnected = true;
      polishConnected(root);
      return;
    }
    root.setAttribute(MARK, "1");
    walkText(root);
    expandAll(root);
    hideSetupError(root);
    recommendGrok(root);
    bindProviderClicks(root);
  }

  function tick() {
    try {
      var bodyText = document.body ? labelOf(document.body) : "";
      if (looksLikeConnectedConfirm(bodyText)) {
        sawConnected = true;
        polishConnected(document.body);
        return;
      }
      if (sawConnected) {
        hideProviderList(document.body);
        walkText(document.body);
        hideSetupError(document.body);
        return;
      }
      var root = findProviderRoot();
      if (root) {
        sawProviderUi = true;
        polish(root);
      } else if (sawProviderUi) {
        scheduleInherit();
      }
      walkText(document.body);
      hideSetupError(document.body);
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
