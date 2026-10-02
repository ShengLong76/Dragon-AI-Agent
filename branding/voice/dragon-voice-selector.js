/* Dragon AI Agent — GPT | Grok voice selector + overlay Grok duplex.
 * Official xAI Speech-to-Speech (do not invent endpoints):
 *   wss://api.x.ai/v1/realtime?model=grok-voice-latest
 *   POST https://api.x.ai/v1/realtime/client_secrets  {expires_after:{seconds:300}}
 *   Browser WS subprotocol xai-client-secret.<value>
 *   session.update voice=eve, turn_detection.server_vad, audio/pcm 24000
 *   input_audio_buffer.append {audio: base64 PCM16}
 *   response.output_audio.delta / response.audio.delta
 * GPT stays Hermes gpt-live. This IIFE only hosts Grok duplex in the Electron renderer.
 */
(function () {
  var API = "http://127.0.0.1:8654";
  var KEY = "dragon.voice.provider";
  var REALTIME = "wss://api.x.ai/v1/realtime?model=grok-voice-latest";
  var SAMPLE_RATE = 24000;
  var session = null;

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function current() {
    try {
      return localStorage.getItem(KEY) || "gpt";
    } catch (e) {
      return "gpt";
    }
  }

  function persist(id) {
    try {
      localStorage.setItem(KEY, id);
    } catch (e) {}
  }

  function option(id, label) {
    var b = document.createElement("button");
    b.type = "button";
    b.setAttribute("data-dragon-voice-option", id);
    b.setAttribute("role", "radio");
    b.textContent = label;
    return b;
  }

  function setStatus(root, text) {
    var status = $("[data-dragon-voice-status]", root);
    if (status) status.textContent = text || "";
  }

  function paint(root, id) {
    root.querySelectorAll("[data-dragon-voice-option]").forEach(function (btn) {
      var on = btn.getAttribute("data-dragon-voice-option") === id;
      btn.setAttribute("aria-checked", on ? "true" : "false");
      btn.tabIndex = on ? 0 : -1;
    });
    var talk = $("[data-dragon-grok-talk]", root) || $("[data-dragon-grok-talk]");
    if (talk) {
      talk.hidden = id !== "grok";
      if (id !== "grok") talk.setAttribute("hidden", "");
      else talk.removeAttribute("hidden");
      talk.textContent = session && session.live ? "Stop Grok" : "Start conversation";
      talk.setAttribute("aria-label", session && session.live ? "Stop Grok" : "Start conversation — Talk with Grok");
      talk.setAttribute("aria-pressed", session && session.live ? "true" : "false");
    }
    if (id === "grok") {
      setStatus(root, session && session.live ? "Grok duplex live (xAI grok-voice-latest)." : "Grok duplex ready. GPT stays available.");
    } else {
      setStatus(root, "GPT voice (OpenAI gpt-live). Use the Hermes mic for duplex GPT.");
    }
  }

  function pcm16ToBase64(int16) {
    var bytes = new Uint8Array(int16.buffer, int16.byteOffset, int16.byteLength);
    var bin = "";
    var step = 0x8000;
    for (var i = 0; i < bytes.length; i += step) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
    }
    return btoa(bin);
  }

  function base64ToInt16(b64) {
    var binary = atob(b64);
    var bytes = new Uint8Array(binary.length);
    for (var i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Int16Array(bytes.buffer);
  }

  function downsampleToPcm16(float32, inRate, outRate) {
    var ratio = inRate / outRate;
    var outLen = Math.max(1, Math.floor(float32.length / ratio));
    var pcm = new Int16Array(outLen);
    for (var i = 0; i < outLen; i++) {
      var s = float32[Math.min(float32.length - 1, Math.floor(i * ratio))];
      s = Math.max(-1, Math.min(1, s));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm;
  }

  function playPcm16(ctx, int16, rate, when) {
    var buffer = ctx.createBuffer(1, int16.length, rate);
    var data = buffer.getChannelData(0);
    for (var i = 0; i < int16.length; i++) data[i] = int16[i] / 32768;
    var src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(ctx.destination);
    src.start(when);
    return when + buffer.duration;
  }

  function tokenValue(payload) {
    if (!payload) return "";
    if (payload.value) return String(payload.value);
    if (payload.token && payload.token.value) return String(payload.token.value);
    return "";
  }

  function stopDuplex() {
    if (!session) return;
    session.live = false;
    try {
      if (session.processor) session.processor.disconnect();
    } catch (e) {}
    try {
      if (session.source) session.source.disconnect();
    } catch (e) {}
    try {
      if (session.stream) session.stream.getTracks().forEach(function (t) { t.stop(); });
    } catch (e) {}
    try {
      if (session.ws) session.ws.close();
    } catch (e) {}
    try {
      if (session.audioCtx) session.audioCtx.close();
    } catch (e) {}
    session = null;
  }

  function startDuplex(root) {
    setStatus(root, "Minting xAI ephemeral token…");
    fetch(API + "/api/voice/ephemeral", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var value = tokenValue(data);
        if (!data.ok || !value) {
          setStatus(root, data.message || data.error || "Need XAI_API_KEY on the voice helper for Grok duplex.");
          return;
        }
        var url = data.realtimeUrl || REALTIME;
        var ws = new WebSocket(url, ["xai-client-secret." + value]);
        ws.binaryType = "arraybuffer";
        var local = { live: true, ws: ws, nextPlay: 0 };
        session = local;
        paint(root, "grok");
        ws.onopen = function () {
          var update = data.session || {
            type: "session.update",
            session: {
              voice: "eve",
              turn_detection: { type: "server_vad" },
              audio: {
                input: { format: { type: "audio/pcm", rate: SAMPLE_RATE } },
                output: { format: { type: "audio/pcm", rate: SAMPLE_RATE } }
              }
            }
          };
          ws.send(JSON.stringify(update));
          setStatus(root, "Grok duplex connected. Speak — server VAD turn-taking.");
          navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } })
            .then(function (stream) {
              if (!session || session.ws !== ws) {
                stream.getTracks().forEach(function (t) { t.stop(); });
                return;
              }
              var ctx = new AudioContext();
              var source = ctx.createMediaStreamSource(stream);
              var processor = ctx.createScriptProcessor(4096, 1, 1);
              var mute = ctx.createGain();
              mute.gain.value = 0;
              processor.onaudioprocess = function (ev) {
                if (!session || session.ws !== ws || ws.readyState !== 1) return;
                var input = ev.inputBuffer.getChannelData(0);
                var pcm = downsampleToPcm16(input, ev.inputBuffer.sampleRate, SAMPLE_RATE);
                ws.send(JSON.stringify({ type: "input_audio_buffer.append", audio: pcm16ToBase64(pcm) }));
              };
              source.connect(processor);
              processor.connect(mute);
              mute.connect(ctx.destination);
              session.stream = stream;
              session.audioCtx = ctx;
              session.source = source;
              session.processor = processor;
              session.playCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
              if (session.playCtx.resume) session.playCtx.resume();
              session.nextPlay = session.playCtx.currentTime;
            })
            .catch(function () {
              setStatus(root, "Microphone permission is required for Grok duplex.");
              stopDuplex();
              paint(root, "grok");
            });
        };
        ws.onmessage = function (ev) {
          if (typeof ev.data !== "string") return;
          var event;
          try { event = JSON.parse(ev.data); } catch (e) { return; }
          var kind = event.type || "";
          if (kind === "response.output_audio.delta" || kind === "response.audio.delta") {
            var chunk = event.delta || event.audio;
            if (!chunk || !session || !session.playCtx) return;
            session.nextPlay = playPcm16(session.playCtx, base64ToInt16(chunk), SAMPLE_RATE, Math.max(session.playCtx.currentTime, session.nextPlay));
            return;
          }
          if (kind === "input_audio_buffer.speech_started") {
            setStatus(root, "Grok is listening…");
            return;
          }
          if (kind === "input_audio_buffer.speech_stopped") {
            setStatus(root, "Grok is answering…");
            return;
          }
          if (kind === "error") {
            setStatus(root, (event.error && event.error.message) || "Grok duplex error");
          }
        };
        ws.onerror = function () {
          setStatus(root, "Grok duplex WebSocket error.");
        };
        ws.onclose = function () {
          stopDuplex();
          paint(root, current());
        };
      })
      .catch(function () {
        setStatus(root, "Voice helper is not running on 127.0.0.1:8654. Cannot mint an ephemeral token.");
      });
  }

  function toggleGrok(root) {
    if (session && session.live) {
      stopDuplex();
      paint(root, "grok");
      setStatus(root, "Grok duplex stopped. GPT stays available.");
      return;
    }
    startDuplex(root);
  }

  function select(root, id, saveRemote) {
    if (id !== "gpt" && id !== "grok") id = "gpt";
    if (id === "gpt") stopDuplex();
    persist(id);
    paint(root, id);
    try {
      window.dispatchEvent(new CustomEvent("dragon-voice-provider", { detail: { provider: id } }));
    } catch (e) {}
    if (!saveRemote) return;
    fetch(API + "/api/voice/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: id })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.error) {
          setStatus(root, data.message || data.error);
          return;
        }
        paint(root, id);
      })
      .catch(function () {
        setStatus(root, id === "grok"
          ? "Grok selected locally. Start the helper on 127.0.0.1:8654 to talk duplex."
          : "GPT selected. Voice helper is not running on 127.0.0.1:8654.");
      });
  }

  function isOwnControl(el) {
    if (!el || !el.getAttribute) return false;
    return !!(el.getAttribute("data-dragon-voice-option")
      || el.getAttribute("data-dragon-grok-talk")
      || el.getAttribute("data-dragon-voice-provider")
      || el.getAttribute("data-dragon-ai-composer-action")
      || el.getAttribute("data-dragon-ai-composer-chrome"));
  }

  function findComposerHost() {
    return document.querySelector('[data-slot="aui_composer"]')
      || document.querySelector('[data-slot="composer"]')
      || document.querySelector("textarea")
      || document.querySelector("form");
  }

  function findComposerAction(host) {
    if (!host) return null;
    var selectors = [
      '[data-slot="aui_composer-speech"]',
      '[data-slot="composer-speech"]',
      '[data-slot="aui_composer-actions"] button:last-child',
      'button[aria-label*="voice" i]',
      'button[aria-label*="talk" i]',
      'button[aria-label*="mic" i]',
      'button[aria-label*="speech" i]',
      'button[aria-label*="start conversation" i]'
    ];
    var i;
    for (i = 0; i < selectors.length; i++) {
      try {
        var el = host.querySelector(selectors[i]);
        if (el && !isOwnControl(el)) return el;
      } catch (e) {}
    }
    var buttons = host.querySelectorAll("button");
    var last = null;
    for (i = 0; i < buttons.length; i++) {
      if (!isOwnControl(buttons[i])) last = buttons[i];
    }
    return last;
  }

  function placeTalk(talk, host) {
    var cluster = document.querySelector("[data-dragon-ai-composer-action]");
    if (!cluster) {
      cluster = document.createElement("div");
      cluster.setAttribute("data-dragon-ai-composer-action", "true");
    }
    var action = findComposerAction(host);
    if (action && action.parentNode) {
      if (cluster.parentNode !== action.parentNode) {
        action.parentNode.insertBefore(cluster, action);
      }
    } else if (host && cluster.parentNode !== host) {
      host.appendChild(cluster);
    }
    if (talk.parentNode !== cluster) cluster.appendChild(talk);
  }

  function mount() {
    var existing = document.querySelector("[data-dragon-voice-provider]");
    var host = findComposerHost();
    if (existing) {
      var moved = $("[data-dragon-grok-talk]");
      if (moved && host) placeTalk(moved, host);
      return;
    }
    if (!host) return;
    if (host.setAttribute) host.setAttribute("data-dragon-ai-composer-chrome", "true");
    var root = document.createElement("div");
    root.setAttribute("data-dragon-voice-provider", "true");
    root.setAttribute("data-dragon-ai-composer-chrome", "true");
    root.setAttribute("role", "radiogroup");
    root.setAttribute("aria-label", "Voice chat provider");
    var legend = document.createElement("span");
    legend.setAttribute("data-dragon-voice-legend", "true");
    legend.textContent = "Voice";
    var gpt = option("gpt", "GPT");
    var grok = option("grok", "Grok");
    var talk = document.createElement("button");
    talk.type = "button";
    talk.setAttribute("data-dragon-grok-talk", "true");
    talk.textContent = "Start conversation";
    talk.setAttribute("aria-label", "Start conversation — Talk with Grok");
    talk.hidden = true;
    var status = document.createElement("p");
    status.setAttribute("data-dragon-voice-status", "true");
    status.setAttribute("role", "status");
    gpt.addEventListener("click", function () { select(root, "gpt", true); });
    grok.addEventListener("click", function () { select(root, "grok", true); });
    talk.addEventListener("click", function () { toggleGrok(root); });
    root.appendChild(legend);
    root.appendChild(gpt);
    root.appendChild(grok);
    root.appendChild(status);
    if (host.parentNode && host.tagName && host.tagName.toLowerCase() === "textarea") {
      host.parentNode.insertBefore(root, host);
    } else {
      host.insertBefore(root, host.firstChild);
    }
    placeTalk(talk, host);
    var start = current();
    paint(root, start);
    fetch(API + "/api/voice/selection")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.provider) {
          persist(data.provider);
          paint(root, data.provider);
        }
      })
      .catch(function () {});
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
