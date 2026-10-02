/* Dragon AI Agent — Grok-Bot floating voice waveform.
 * Chat-screen GPT/Grok pills are gone. Composer right-side waveform
 * opens a capsule (avatar | purple bars | gear | chat | mic | red X).
 * Gear opens Voice settings: official xAI voice, speed, language,
 * interrupt. Duplex is Settings Voice mode grok-live:
 *   wss://api.x.ai/v1/realtime?model=grok-voice-latest
 *   POST https://api.x.ai/v1/realtime/client_secrets  {expires_after:{seconds:300}}
 *   Browser WS subprotocol xai-client-secret.<value>
 *   session.update voice, turn_detection.server_vad, audio/pcm 24000
 *   input_audio_buffer.append {audio: base64 PCM16}
 *   response.output_audio.delta / response.audio.delta
 * Built-in voices only (docs.x.ai): eve, ara, rex, sal, leo.
 */
(function () {
  var API = "http://127.0.0.1:8654";
  var PREF_KEY = "dragon.voice.prefs";
  var REALTIME = "wss://api.x.ai/v1/realtime?model=grok-voice-latest";
  var SAMPLE_RATE = 24000;
  var VOICES = [
    { id: "eve", label: "Eve", tone: "Energetic, upbeat" },
    { id: "ara", label: "Ara", tone: "Warm, friendly" },
    { id: "rex", label: "Rex", tone: "Confident, clear" },
    { id: "sal", label: "Sal", tone: "Smooth, balanced" },
    { id: "leo", label: "Leo", tone: "Authoritative, strong" }
  ];
  var LANGUAGES = [
    { id: "en", label: "English" },
    { id: "auto", label: "Auto-detect" },
    { id: "es-ES", label: "Spanish" },
    { id: "fr", label: "French" },
    { id: "de", label: "German" },
    { id: "ja", label: "Japanese" },
    { id: "zh", label: "Chinese" }
  ];
  var BAR_COUNT = 18;
  var session = null;
  var prefs = { voice: "eve", speed: 1, language: "en", interrupt: true };
  var roots = { widget: null, trigger: null, host: null };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function loadPrefs() {
    try {
      var raw = localStorage.getItem(PREF_KEY);
      if (!raw) return;
      var parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object") applyPrefShape(parsed);
    } catch (e) {}
  }

  function applyPrefShape(data) {
    if (!data) return;
    var voice = String(data.voice || "").trim().toLowerCase();
    var i;
    for (i = 0; i < VOICES.length; i++) {
      if (VOICES[i].id === voice) prefs.voice = voice;
    }
    var speed = Number(data.speed);
    if (speed && speed >= 0.75 && speed <= 2) prefs.speed = speed;
    var language = String(data.language || "").trim();
    for (i = 0; i < LANGUAGES.length; i++) {
      if (LANGUAGES[i].id === language) prefs.language = language;
    }
    if (typeof data.interrupt === "boolean") prefs.interrupt = data.interrupt;
  }

  function persistPrefs(remote) {
    try {
      localStorage.setItem(PREF_KEY, JSON.stringify(prefs));
    } catch (e) {}
    if (!remote) return;
    fetch(API + "/api/voice/prefs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(prefs)
    }).catch(function () {});
  }

  function svgIcon(path, view) {
    return (
      '<svg viewBox="' + (view || "0 0 24 24") + '" width="18" height="18" aria-hidden="true" focusable="false">' +
      '<path fill="currentColor" d="' + path + '"></path></svg>'
    );
  }

  function waveformIcon() {
    return (
      '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">' +
      '<rect x="3" y="8" width="2.2" height="8" rx="1" fill="currentColor"></rect>' +
      '<rect x="7.2" y="5" width="2.2" height="14" rx="1" fill="currentColor"></rect>' +
      '<rect x="11.4" y="3" width="2.2" height="18" rx="1" fill="currentColor"></rect>' +
      '<rect x="15.6" y="6" width="2.2" height="12" rx="1" fill="currentColor"></rect>' +
      '<rect x="19.8" y="9" width="2.2" height="6" rx="1" fill="currentColor"></rect>' +
      "</svg>"
    );
  }

  function pcm16ToBase64(int16) {
    var bytes = new Uint8Array(int16.buffer, int16.byteOffset, int16.byteLength);
    var bin = "";
    var step = 0x8000;
    var i;
    for (i = 0; i < bytes.length; i += step) {
      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + step));
    }
    return btoa(bin);
  }

  function base64ToInt16(b64) {
    var binary = atob(b64);
    var bytes = new Uint8Array(binary.length);
    var i;
    for (i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new Int16Array(bytes.buffer);
  }

  function downsampleToPcm16(float32, inRate, outRate) {
    var ratio = inRate / outRate;
    var outLen = Math.max(1, Math.floor(float32.length / ratio));
    var pcm = new Int16Array(outLen);
    var i;
    var s;
    for (i = 0; i < outLen; i++) {
      s = float32[Math.min(float32.length - 1, Math.floor(i * ratio))];
      s = Math.max(-1, Math.min(1, s));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm;
  }

  function playPcm16(ctx, int16, rate, when) {
    var buffer = ctx.createBuffer(1, int16.length, rate);
    var data = buffer.getChannelData(0);
    var i;
    for (i = 0; i < int16.length; i++) data[i] = int16[i] / 32768;
    var src = ctx.createBufferSource();
    src.buffer = buffer;
    var speed = Number(prefs.speed) || 1;
    try {
      src.playbackRate.value = speed;
    } catch (e) {}
    src.connect(ctx.destination);
    src.start(when);
    return when + buffer.duration / speed;
  }

  function tokenValue(payload) {
    if (!payload) return "";
    if (payload.value) return String(payload.value);
    if (payload.token && payload.token.value) return String(payload.token.value);
    return "";
  }

  function setStatus(text) {
    var status = roots.widget && $("[data-dragon-voice-status]", roots.widget);
    if (status) status.textContent = text || "";
  }

  function setState(state) {
    if (!roots.widget) return;
    roots.widget.setAttribute("data-state", state);
    if (roots.trigger) roots.trigger.setAttribute("aria-pressed", state === "hidden" ? "false" : "true");
  }

  function rmsLevel(samples) {
    var sum = 0;
    var i;
    for (i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
    return Math.min(1, Math.sqrt(sum / Math.max(1, samples.length)) * 3.2);
  }

  function paintWave(level) {
    if (!roots.widget) return;
    var bars = roots.widget.querySelectorAll("[data-dragon-voice-wave] i");
    var i;
    var height;
    for (i = 0; i < bars.length; i++) {
      height = 18 + Math.round(level * 72 * (0.45 + ((i * 17) % 10) / 14));
      bars[i].style.height = height + "%";
    }
  }

  function paintPrefs() {
    if (!roots.widget) return;
    var voice = $("[data-dragon-voice-pref='voice']", roots.widget);
    var speed = $("[data-dragon-voice-pref='speed']", roots.widget);
    var language = $("[data-dragon-voice-pref='language']", roots.widget);
    var interrupt = $("[data-dragon-voice-pref='interrupt']", roots.widget);
    var speedValue = $("[data-dragon-voice-speed-value]", roots.widget);
    if (voice) voice.value = prefs.voice;
    if (speed) speed.value = String(prefs.speed);
    if (language) language.value = prefs.language;
    if (interrupt) interrupt.checked = !!prefs.interrupt;
    if (speedValue) speedValue.textContent = String(prefs.speed).replace(/\.0$/, "") + "×";
  }

  function settingsOpen() {
    var panel = roots.widget && $("[data-dragon-voice-settings-panel]", roots.widget);
    return !!(panel && !panel.hidden);
  }

  function setSettingsOpen(open) {
    if (!roots.widget) return;
    var panel = $("[data-dragon-voice-settings-panel]", roots.widget);
    var gear = $("[data-dragon-voice-gear]", roots.widget);
    if (!panel || !gear) return;
    panel.hidden = !open;
    gear.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      var first = $("[data-dragon-voice-pref='voice']", panel);
      if (first && first.focus) first.focus();
    }
  }

  function pushSessionVoice() {
    if (!session || !session.ws || session.ws.readyState !== 1) return;
    session.ws.send(JSON.stringify({
      type: "session.update",
      session: {
        voice: prefs.voice,
        turn_detection: { type: "server_vad" },
        audio: {
          input: { format: { type: "audio/pcm", rate: SAMPLE_RATE } },
          output: { format: { type: "audio/pcm", rate: SAMPLE_RATE } }
        }
      }
    }));
  }

  function stopDuplex() {
    if (!session) return;
    session.live = false;
    try { if (session.raf) cancelAnimationFrame(session.raf); } catch (e) {}
    try { if (session.processor) session.processor.disconnect(); } catch (e) {}
    try { if (session.source) session.source.disconnect(); } catch (e) {}
    try { if (session.stream) session.stream.getTracks().forEach(function (t) { t.stop(); }); } catch (e) {}
    try { if (session.ws) session.ws.close(); } catch (e) {}
    try { if (session.audioCtx) session.audioCtx.close(); } catch (e) {}
    try { if (session.playCtx) session.playCtx.close(); } catch (e) {}
    session = null;
    paintWave(0.18);
  }

  function startDuplex() {
    setStatus("Minting xAI ephemeral token…");
    setState("connecting");
    fetch(API + "/api/voice/ephemeral", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ voice: prefs.voice })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var value = tokenValue(data);
        if (!data.ok || !value) {
          setStatus(data.message || data.error || "Need XAI_API_KEY on the voice helper for Grok Voice.");
          setState("error");
          return;
        }
        var url = data.realtimeUrl || REALTIME;
        var ws = new WebSocket(url, ["xai-client-secret." + value]);
        ws.binaryType = "arraybuffer";
        var local = { live: true, ws: ws, nextPlay: 0, muted: false, speaking: false };
        session = local;
        setState("live");
        ws.onopen = function () {
          var update = data.session || {
            type: "session.update",
            session: {
              voice: prefs.voice,
              turn_detection: { type: "server_vad" },
              audio: {
                input: { format: { type: "audio/pcm", rate: SAMPLE_RATE } },
                output: { format: { type: "audio/pcm", rate: SAMPLE_RATE } }
              }
            }
          };
          if (update.session) update.session.voice = prefs.voice;
          ws.send(JSON.stringify(update));
          setStatus("Grok Voice live. Speak — server VAD turn-taking.");
          navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
          })
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
                var level = rmsLevel(input);
                if (!session.speaking) paintWave(session.muted ? 0.12 : Math.max(0.16, level));
                if (session.muted) return;
                if (!prefs.interrupt && session.speaking) return;
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
              setStatus("Microphone permission is required for Grok Voice.");
              stopDuplex();
              setState("error");
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
            session.speaking = true;
            session.nextPlay = playPcm16(
              session.playCtx,
              base64ToInt16(chunk),
              SAMPLE_RATE,
              Math.max(session.playCtx.currentTime, session.nextPlay)
            );
            paintWave(0.72);
            return;
          }
          if (kind === "input_audio_buffer.speech_started") {
            if (session) session.speaking = false;
            setStatus("Listening…");
            setState("listening");
            return;
          }
          if (kind === "input_audio_buffer.speech_stopped") {
            setStatus("Grok is answering…");
            setState("speaking");
            return;
          }
          if (kind === "response.done" || kind === "response.output_audio.done") {
            if (session) session.speaking = false;
            setState("live");
            return;
          }
          if (kind === "error") {
            setStatus((event.error && event.error.message) || "Grok Voice error");
          }
        };
        ws.onerror = function () {
          setStatus("Grok Voice WebSocket error.");
        };
        ws.onclose = function () {
          var wasLive = session && session.ws === ws;
          if (wasLive) stopDuplex();
          if (roots.widget && !roots.widget.hidden) setState("idle");
        };
      })
      .catch(function () {
        setStatus("Voice helper is not running on 127.0.0.1:8654. Cannot mint an ephemeral token.");
        setState("error");
      });
  }

  function ensureGrokLive() {
    fetch(API + "/api/voice/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: "grok-live", voiceChatMode: "grok-live" })
    }).catch(function () {});
  }

  function openWidget() {
    if (!roots.widget) return;
    roots.widget.hidden = false;
    roots.widget.removeAttribute("hidden");
    setSettingsOpen(false);
    setState(session && session.live ? "live" : "idle");
    ensureGrokLive();
    persistPrefs(true);
    if (!(session && session.live)) startDuplex();
    try {
      window.dispatchEvent(new CustomEvent("dragon-voice-widget", { detail: { open: true, mode: "grok-live" } }));
    } catch (e) {}
  }

  function closeWidget(stop) {
    setSettingsOpen(false);
    if (stop) stopDuplex();
    if (roots.widget) {
      roots.widget.hidden = true;
      roots.widget.setAttribute("hidden", "");
    }
    setState("hidden");
    if (roots.trigger && roots.trigger.focus) roots.trigger.focus();
  }

  function toggleMute() {
    if (!session) return;
    session.muted = !session.muted;
    var mic = roots.widget && $("[data-dragon-voice-mic]", roots.widget);
    if (mic) {
      mic.setAttribute("aria-pressed", session.muted ? "true" : "false");
      mic.setAttribute("aria-label", session.muted ? "Unmute microphone" : "Mute microphone");
      mic.setAttribute("data-muted", session.muted ? "true" : "false");
    }
    setStatus(session.muted ? "Microphone muted." : "Microphone on.");
  }

  function onPrefChange(name, value) {
    if (name === "voice") prefs.voice = value;
    if (name === "speed") prefs.speed = Number(value) || 1;
    if (name === "language") prefs.language = value;
    if (name === "interrupt") prefs.interrupt = !!value;
    paintPrefs();
    persistPrefs(true);
    if (name === "voice") {
      pushSessionVoice();
      setStatus("Voice set to " + prefs.voice + ".");
    }
    if (name === "speed") setStatus("Playback speed " + prefs.speed + "×.");
  }

  function isOwnControl(el) {
    if (!el || !el.getAttribute) return false;
    return !!(
      el.getAttribute("data-dragon-voice-trigger") ||
      el.getAttribute("data-dragon-voice-widget") ||
      el.getAttribute("data-dragon-voice-gear") ||
      el.getAttribute("data-dragon-ai-composer-action") ||
      el.getAttribute("data-dragon-ai-composer-chrome")
    );
  }

  function findComposerHost() {
    return document.querySelector('[data-slot="aui_composer"]')
      || document.querySelector('[data-slot="composer"]')
      || document.querySelector("textarea")
      || document.querySelector("form");
  }

  function findChatPane() {
    return document.querySelector('[data-slot="aui_thread"]')
      || document.querySelector('[data-slot="thread"]')
      || document.querySelector('[data-slot="aui_viewport"]')
      || document.querySelector('[data-chat-surface]')
      || document.querySelector("main")
      || document.body;
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
    var el;
    for (i = 0; i < selectors.length; i++) {
      try {
        el = host.querySelector(selectors[i]);
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

  function placeTrigger(trigger, host) {
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
      if (/speech|voice|mic|talk/i.test((action.getAttribute("data-slot") || "") + " " + (action.getAttribute("aria-label") || ""))) {
        action.setAttribute("data-dragon-voice-native-hidden", "true");
      }
    } else if (host && cluster.parentNode !== host) {
      host.appendChild(cluster);
    }
    if (trigger.parentNode !== cluster) cluster.appendChild(trigger);
  }

  function placeWidget(widget) {
    var pane = findChatPane();
    if (!pane) return;
    if (pane.getAttribute && !pane.getAttribute("data-dragon-voice-pane")) {
      pane.setAttribute("data-dragon-voice-pane", "true");
    }
    if (widget.parentNode !== pane) pane.appendChild(widget);
  }

  function avatarSrc() {
    var img = document.querySelector("[data-dragon-ai-sidebar-brand] img")
      || document.querySelector('[data-sidebar="menu-button"][data-active] img')
      || document.querySelector("[data-roster-key][data-active] img");
    if (img && img.getAttribute("src")) return img.getAttribute("src");
    return "dragon-ai-branding/dragon-ai-agent-logo.svg";
  }

  function optionList(rows, valueKey) {
    var html = "";
    var i;
    for (i = 0; i < rows.length; i++) {
      html += '<option value="' + rows[i].id + '">' + rows[i].label;
      if (rows[i][valueKey]) html += " — " + rows[i][valueKey];
      html += "</option>";
    }
    return html;
  }

  function buildTrigger() {
    var trigger = document.createElement("button");
    trigger.type = "button";
    trigger.setAttribute("data-dragon-voice-trigger", "true");
    trigger.setAttribute("aria-label", "Talk with Grok");
    trigger.setAttribute("aria-pressed", "false");
    trigger.setAttribute("title", "Talk with Grok");
    trigger.innerHTML = waveformIcon();
    trigger.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      if (roots.widget && !roots.widget.hidden) closeWidget(true);
      else openWidget();
    });
    return trigger;
  }

  function buildWidget() {
    var widget = document.createElement("div");
    widget.setAttribute("data-dragon-voice-widget", "true");
    widget.setAttribute("data-dragon-voice-provider", "true");
    widget.setAttribute("hidden", "");
    widget.hidden = true;
    widget.setAttribute("data-state", "hidden");

    var capsule = document.createElement("div");
    capsule.setAttribute("data-dragon-voice-capsule", "true");
    capsule.setAttribute("role", "toolbar");
    capsule.setAttribute("aria-label", "Grok Voice");

    var avatar = document.createElement("div");
    avatar.setAttribute("data-dragon-voice-avatar", "true");
    var pic = document.createElement("img");
    pic.alt = "";
    pic.setAttribute("aria-hidden", "true");
    pic.src = avatarSrc();
    avatar.appendChild(pic);

    var wave = document.createElement("div");
    wave.setAttribute("data-dragon-voice-wave", "true");
    wave.setAttribute("aria-hidden", "true");
    var i;
    for (i = 0; i < BAR_COUNT; i++) {
      var bar = document.createElement("i");
      bar.style.setProperty("--i", String(i));
      wave.appendChild(bar);
    }

    var gear = document.createElement("button");
    gear.type = "button";
    gear.setAttribute("data-dragon-voice-gear", "true");
    gear.setAttribute("aria-label", "Voice settings");
    gear.setAttribute("aria-expanded", "false");
    gear.setAttribute("aria-controls", "dragon-voice-settings-panel");
    gear.innerHTML = svgIcon("M19.14 12.94a7.43 7.43 0 0 0 .05-.94 7.43 7.43 0 0 0-.05-.94l2.03-1.58a.5.5 0 0 0 .12-.64l-1.92-3.32a.5.5 0 0 0-.61-.22l-2.39.96a7.16 7.16 0 0 0-1.63-.94l-.36-2.54A.5.5 0 0 0 13.9 2h-3.8a.5.5 0 0 0-.49.42l-.36 2.54c-.58.24-1.13.55-1.63.94l-2.39-.96a.5.5 0 0 0-.61.22L2.7 8.48a.5.5 0 0 0 .12.64L4.85 10.7a7.43 7.43 0 0 0-.05.94 7.43 7.43 0 0 0 .05.94L2.82 14.16a.5.5 0 0 0-.12.64l1.92 3.32a.5.5 0 0 0 .61.22l2.39-.96c.5.39 1.05.7 1.63.94l.36 2.54a.5.5 0 0 0 .49.42h3.8a.5.5 0 0 0 .49-.42l.36-2.54c.58-.24 1.13-.55 1.63-.94l2.39.96a.5.5 0 0 0 .61-.22l1.92-3.32a.5.5 0 0 0-.12-.64zM12 15.5A3.5 3.5 0 1 1 12 8.5a3.5 3.5 0 0 1 0 7z");
    gear.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      setSettingsOpen(!settingsOpen());
    });

    var chat = document.createElement("button");
    chat.type = "button";
    chat.setAttribute("data-dragon-voice-chat", "true");
    chat.setAttribute("aria-label", "Return to chat");
    chat.innerHTML = svgIcon("M4 4h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H8l-4 4V6a2 2 0 0 1 2-2zm3 5h10v2H7zm0 4h7v2H7z");
    chat.addEventListener("click", function (ev) {
      ev.preventDefault();
      closeWidget(true);
    });

    var mic = document.createElement("button");
    mic.type = "button";
    mic.setAttribute("data-dragon-voice-mic", "true");
    mic.setAttribute("aria-label", "Mute microphone");
    mic.setAttribute("aria-pressed", "false");
    mic.innerHTML = svgIcon("M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.92V21h2v-3.08A7 7 0 0 0 19 11z");
    mic.addEventListener("click", function (ev) {
      ev.preventDefault();
      toggleMute();
    });

    var end = document.createElement("button");
    end.type = "button";
    end.setAttribute("data-dragon-voice-end", "true");
    end.setAttribute("aria-label", "End voice");
    end.innerHTML = svgIcon("M18.3 5.71a1 1 0 0 0-1.41 0L12 10.59 7.11 5.7A1 1 0 0 0 5.7 7.11L10.59 12 5.7 16.89a1 1 0 1 0 1.41 1.41L12 13.41l4.89 4.89a1 1 0 0 0 1.41-1.41L13.41 12l4.89-4.89a1 1 0 0 0 0-1.4z");
    end.addEventListener("click", function (ev) {
      ev.preventDefault();
      closeWidget(true);
    });

    capsule.appendChild(avatar);
    capsule.appendChild(wave);
    capsule.appendChild(gear);
    capsule.appendChild(chat);
    capsule.appendChild(mic);
    capsule.appendChild(end);

    var panel = document.createElement("div");
    panel.id = "dragon-voice-settings-panel";
    panel.setAttribute("data-dragon-voice-settings-panel", "true");
    panel.setAttribute("role", "dialog");
    panel.setAttribute("aria-label", "Voice settings");
    panel.hidden = true;
    panel.innerHTML =
      '<p data-dragon-voice-settings-title>Voice settings</p>' +
      '<label data-dragon-voice-field>' +
        "<span>Voice</span>" +
        '<select data-dragon-voice-pref="voice" aria-label="Grok voice">' +
          optionList(VOICES, "tone") +
        "</select>" +
      "</label>" +
      '<label data-dragon-voice-field>' +
        '<span>Speed <em data-dragon-voice-speed-value>1×</em></span>' +
        '<input type="range" min="0.75" max="2" step="0.25" value="1" data-dragon-voice-pref="speed" aria-label="Playback speed">' +
      "</label>" +
      '<label data-dragon-voice-field>' +
        "<span>Language</span>" +
        '<select data-dragon-voice-pref="language" aria-label="Voice language">' +
          optionList(LANGUAGES) +
        "</select>" +
      "</label>" +
      '<label data-dragon-voice-check>' +
        '<input type="checkbox" data-dragon-voice-pref="interrupt" checked>' +
        "<span>Interrupt when I speak</span>" +
      "</label>";

    panel.addEventListener("change", function (ev) {
      var el = ev.target;
      if (!el || !el.getAttribute) return;
      var name = el.getAttribute("data-dragon-voice-pref");
      if (!name) return;
      onPrefChange(name, name === "interrupt" ? el.checked : el.value);
    });
    panel.addEventListener("input", function (ev) {
      var el = ev.target;
      if (!el || el.getAttribute("data-dragon-voice-pref") !== "speed") return;
      onPrefChange("speed", el.value);
    });

    var status = document.createElement("p");
    status.setAttribute("data-dragon-voice-status", "true");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");

    widget.appendChild(capsule);
    widget.appendChild(panel);
    widget.appendChild(status);
    return widget;
  }

  function onKeydown(ev) {
    if (ev.key !== "Escape") return;
    if (settingsOpen()) {
      ev.preventDefault();
      setSettingsOpen(false);
      return;
    }
    if (roots.widget && !roots.widget.hidden) {
      ev.preventDefault();
      closeWidget(true);
    }
  }

  function syncFromHelper() {
    fetch(API + "/api/voice/selection")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data && data.prefs) applyPrefShape(data.prefs);
        paintPrefs();
      })
      .catch(function () {});
  }

  function mount() {
    var host = findComposerHost();
    var existing = document.querySelector("[data-dragon-voice-widget]");
    if (existing) {
      roots.widget = existing;
      roots.trigger = document.querySelector("[data-dragon-voice-trigger]");
      if (roots.trigger && host) placeTrigger(roots.trigger, host);
      placeWidget(existing);
      return;
    }
    if (!host) return;
    if (host.setAttribute) host.setAttribute("data-dragon-ai-composer-chrome", "true");
    loadPrefs();
    var trigger = buildTrigger();
    var widget = buildWidget();
    roots.trigger = trigger;
    roots.widget = widget;
    roots.host = host;
    placeTrigger(trigger, host);
    placeWidget(widget);
    paintPrefs();
    paintWave(0.2);
    syncFromHelper();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
  document.addEventListener("keydown", onKeydown);
  try {
    new MutationObserver(mount).observe(document.documentElement, { childList: true, subtree: true });
  } catch (e) {}
})();
