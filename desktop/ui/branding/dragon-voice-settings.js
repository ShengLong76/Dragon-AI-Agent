/* Dragon AI Agent — Settings → Voice → Voice conversation mode.
 * Adds Grok Voice beside native Chained and Gpt-live.
 * Selection writes the same voice.voice_chat_mode key gpt-live uses.
 * Does not add chat-screen GPT/Grok pills (those stay out of this surface).
 * Existing overlay duplex (Talk with Grok) is left intact.
 */
(function () {
  var API = "http://127.0.0.1:8654";
  var HOST_ATTR = "data-dragon-voice-mode";
  var MODES = [
    { id: "chained", label: "Chained", provider: "chained" },
    { id: "gpt-live", label: "Gpt-live", provider: "gpt" },
    { id: "grok-live", label: "Grok Voice", provider: "grok" }
  ];
  var currentMode = "";
  var saving = false;

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function labelOf(el) {
    return (el && el.textContent ? el.textContent : "").replace(/\s+/g, " ").trim();
  }

  function normalizeMode(raw) {
    var value = String(raw || "").trim().toLowerCase().replace(/_/g, "-");
    if (value === "gpt" || value === "gptlive" || value === "live") return "gpt-live";
    if (value === "grok" || value === "groklive" || value === "grok-voice") return "grok-live";
    if (value === "chained") return "chained";
    if (value === "gpt-live" || value === "grok-live") return value;
    return "";
  }

  function modeLabel(id) {
    var i;
    for (i = 0; i < MODES.length; i++) {
      if (MODES[i].id === id) return MODES[i].label;
    }
    return id;
  }

  function looksLikeVoiceConversation() {
    var body = document.body;
    if (!body) return false;
    var text = labelOf(body);
    if (/voice chat mode/i.test(text) && /(chained|gpt-live|gpt live)/i.test(text)) return true;
    if (/voice conversation/i.test(text) && /(chained|gpt-live)/i.test(text)) return true;
    return false;
  }

  function findModeLabel() {
    var nodes = document.querySelectorAll("label, p, span, div, dt, h2, h3, legend");
    var i;
    var t;
    for (i = 0; i < nodes.length; i++) {
      t = labelOf(nodes[i]);
      if (/^voice chat mode$/i.test(t) || /^voice conversation mode$/i.test(t)) {
        return nodes[i];
      }
    }
    return null;
  }

  function findNativeControl(label) {
    var node = label;
    var hop;
    var sel;
    for (hop = 0; hop < 8 && node; hop++) {
      sel = node.querySelector("select, [role='combobox'], [role='listbox'], button[aria-haspopup='listbox']");
      if (sel && !sel.getAttribute(HOST_ATTR)) return sel;
      node = node.parentElement;
    }
    return null;
  }

  function findRow(label, native) {
    var node = native || label;
    var hop;
    for (hop = 0; hop < 8 && node && node.parentElement; hop++) {
      if (node.contains(label) && (native ? node.contains(native) : true)) {
        var style = window.getComputedStyle ? window.getComputedStyle(node) : null;
        if (style && (style.display === "flex" || style.display === "grid")) return node;
      }
      node = node.parentElement;
    }
    return (native && native.parentElement) || label.parentElement || label;
  }

  function applyRemote(mode) {
    var id = normalizeMode(mode) || "chained";
    saving = true;
    currentMode = id;
    return fetch(API + "/api/voice/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: id, voiceChatMode: id })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && !data.error && (data.voiceChatMode || data.provider)) {
          currentMode = normalizeMode(data.voiceChatMode || data.provider) || id;
        }
        paint();
        try {
          window.dispatchEvent(new CustomEvent("dragon-voice-mode", { detail: { mode: currentMode } }));
        } catch (e) {}
        return data;
      })
      .catch(function () {
        paint();
      })
      .then(function (data) {
        saving = false;
        return data;
      });
  }

  function paint() {
    document.querySelectorAll("[" + HOST_ATTR + "='select']").forEach(function (sel) {
      if (sel.value !== currentMode) sel.value = currentMode || "chained";
    });
    document.querySelectorAll("[" + HOST_ATTR + "='trigger']").forEach(function (el) {
      el.textContent = modeLabel(currentMode || "chained");
    });
    relabelNativeLists();
  }

  function addNativeOption(select, mode) {
    var exists = false;
    var i;
    for (i = 0; i < select.options.length; i++) {
      if (normalizeMode(select.options[i].value) === mode.id) {
        exists = true;
        select.options[i].textContent = mode.label;
      }
    }
    if (exists) return;
    var opt = document.createElement("option");
    opt.value = mode.id;
    opt.textContent = mode.label;
    select.appendChild(opt);
  }

  function enhanceNativeSelect(select) {
    if (select.getAttribute(HOST_ATTR)) return;
    select.setAttribute(HOST_ATTR, "select");
    MODES.forEach(function (mode) { addNativeOption(select, mode); });
    select.addEventListener("change", function () {
      applyRemote(select.value);
    });
  }

  function relabelNativeLists() {
    var nodes = document.querySelectorAll("[role='option'], [data-radix-collection-item], option");
    var i;
    var t;
    var el;
    for (i = 0; i < nodes.length; i++) {
      el = nodes[i];
      t = labelOf(el);
      if (/^grok-live$/i.test(t) || /^groklive$/i.test(t) || /^grok live$/i.test(t)) {
        if (el.tagName && el.tagName.toLowerCase() === "option") el.textContent = "Grok Voice";
        else if (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) el.textContent = "Grok Voice";
      }
    }
  }

  function injectRadixOption(list) {
    if (!list || list.querySelector("[" + HOST_ATTR + "='option']")) return;
    var sample = list.querySelector("[role='option']");
    var item = document.createElement(sample ? sample.tagName : "div");
    item.setAttribute("role", "option");
    item.setAttribute(HOST_ATTR, "option");
    item.setAttribute("data-value", "grok-live");
    item.setAttribute("tabindex", "0");
    item.textContent = "Grok Voice";
    if (sample && sample.className) item.className = sample.className;
    item.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      applyRemote("grok-live");
    });
    item.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        applyRemote("grok-live");
      }
    });
    list.appendChild(item);
  }

  function mountOverlaySelect(row, native) {
    if (row.querySelector("[" + HOST_ATTR + "='select']")) return;
    var wrap = document.createElement("div");
    wrap.setAttribute(HOST_ATTR, "host");
    var sel = document.createElement("select");
    sel.setAttribute(HOST_ATTR, "select");
    sel.setAttribute("aria-label", "Voice conversation mode");
    MODES.forEach(function (mode) {
      var opt = document.createElement("option");
      opt.value = mode.id;
      opt.textContent = mode.label;
      sel.appendChild(opt);
    });
    sel.value = currentMode || "chained";
    sel.addEventListener("change", function () {
      applyRemote(sel.value);
    });
    wrap.appendChild(sel);
    if (native && native.parentNode) {
      native.setAttribute("data-dragon-voice-mode-native", "true");
      native.setAttribute("aria-hidden", "true");
      native.tabIndex = -1;
      native.parentNode.insertBefore(wrap, native);
    } else {
      row.appendChild(wrap);
    }
  }

  function syncFromHelper() {
    fetch(API + "/api/voice/selection")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data) return;
        currentMode = normalizeMode(data.voiceChatMode || data.provider) || currentMode;
        paint();
      })
      .catch(function () {});
  }

  function mount() {
    if (!looksLikeVoiceConversation()) return;
    var label = findModeLabel();
    if (!label) return;
    var native = findNativeControl(label);
    var row = findRow(label, native);
    if (native && native.tagName && native.tagName.toLowerCase() === "select") {
      enhanceNativeSelect(native);
    } else {
      mountOverlaySelect(row, native);
    }
    document.querySelectorAll("[role='listbox']").forEach(injectRadixOption);
    paint();
    if (!saving && !currentMode) syncFromHelper();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      syncFromHelper();
      mount();
    });
  } else {
    syncFromHelper();
    mount();
  }
  try {
    new MutationObserver(mount).observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) {}
})();
