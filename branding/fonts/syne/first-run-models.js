(function () {
  if (window.__dragonAiFirstRunModels) {
    return;
  }
  window.__dragonAiFirstRunModels = true;

  var STORAGE_KEY = "dragon-ai-models-saved";
  var ROOT_ID = "dragon-ai-first-run-models";

  function saved() {
    try {
      return localStorage.getItem(STORAGE_KEY) === "1";
    } catch (_err) {
      return false;
    }
  }

  function markSaved() {
    try {
      localStorage.setItem(STORAGE_KEY, "1");
    } catch (_err) {}
  }

  function api(path, opts) {
    return fetch(path, opts).then(function (res) {
      return res.json().catch(function () {
        return { ok: false, error: "Models request returned no result." };
      });
    });
  }

  function hide(root) {
    if (root && root.parentNode) {
      root.parentNode.removeChild(root);
    }
    document.documentElement.style.overflow = "";
  }

  function nativeProviderSetupVisible() {
    try {
      var text = document.body ? (document.body.innerText || document.body.textContent || "") : "";
      return /let'?s get you setup|connect a model provider/i.test(text);
    } catch (_err) {
      return false;
    }
  }

  function show(pending) {
    if (document.getElementById(ROOT_ID) || saved() || nativeProviderSetupVisible()) {
      return;
    }
    var root = document.createElement("div");
    root.id = ROOT_ID;
    root.setAttribute("data-airmaze-models", "first-run");
    root.setAttribute("data-dragon-ai-first-run", "models");
    root.innerHTML =
      '<style>' +
      "#" + ROOT_ID + "{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;" +
      "background:rgba(12,12,16,.92);color:#f0f0f5;font-family:Syne,ui-sans-serif,system-ui,sans-serif;}" +
      "#" + ROOT_ID + " .card{width:min(440px,92vw);background:#1c1c20;border:1px solid #50505a;border-radius:16px;padding:28px 24px 20px;}" +
      "#" + ROOT_ID + " h1{margin:0 0 8px;font-size:22px;font-weight:700;}" +
      "#" + ROOT_ID + " .lede{margin:0 0 18px;color:#c4c4ce;font-size:14px;line-height:1.45;}" +
      "#" + ROOT_ID + " label{display:block;margin:0 0 14px;font-size:13px;color:#c4c4ce;}" +
      "#" + ROOT_ID + " select{display:block;width:100%;margin-top:6px;padding:10px 12px;border-radius:10px;" +
      "border:1px solid #50505a;background:#282830;color:#f0f0f5;font:inherit;}" +
      "#" + ROOT_ID + " .note{min-height:1.2em;margin:4px 0 16px;color:#c4c4ce;font-size:13px;}" +
      "#" + ROOT_ID + " .actions{display:flex;gap:10px;flex-wrap:wrap;}" +
      "#" + ROOT_ID + " .primary{background:#c41e3a;color:#fff;border:0;border-radius:999px;padding:10px 18px;font:inherit;cursor:pointer;}" +
      "#" + ROOT_ID + " .skip{background:transparent;color:#c4c4ce;border:1px solid #50505a;border-radius:999px;padding:10px 18px;font:inherit;cursor:pointer;}" +
      "</style>" +
      '<form class="card" id="dragon-ai-models-form">' +
      "<h1>Models</h1>" +
      '<p class="lede">Choose the default chat and image LLMs. Dragon AI Agent uses the xAI Grok login already on this PC. This screen does not ask for a new API key. Personal Assistant is already installed. Teams are added later from Teams Marketplace.</p>' +
      "<label>Default chat LLM" +
      '<select id="dragon-ai-chat-model" name="chat">' +
      '<option value="grok-4.6" selected>Grok (xAI) grok-4.6</option>' +
      '<option value="grok-4.5">Grok (xAI) grok-4.5</option>' +
      '<option value="grok-4.3">Grok (xAI) grok-4.3</option>' +
      "</select></label>" +
      "<label>Default image LLM" +
      '<select id="dragon-ai-image-model" name="image">' +
      '<option value="grok-imagine-image" selected>Grok Imagine</option>' +
      '<option value="grok-imagine-image-quality">Grok Imagine Quality</option>' +
      '<option value="grok-imagine-image-2.0">Grok Imagine 2.0</option>' +
      "</select></label>" +
      '<p class="note" id="dragon-ai-models-note" role="status"></p>' +
      '<div class="actions">' +
      '<button type="submit" class="primary">Continue</button>' +
      '<button type="button" class="skip" id="dragon-ai-models-skip">Skip this step</button>' +
      "</div></form>";
    document.documentElement.style.overflow = "hidden";
    document.body.appendChild(root);
    var note = root.querySelector("#dragon-ai-models-note");
    var form = root.querySelector("#dragon-ai-models-form");
    function setNote(text) {
      if (note) {
        note.textContent = text || "";
      }
    }
    if (pending && pending.chatModel) {
      var chat = root.querySelector("#dragon-ai-chat-model");
      if (chat) {
        chat.value = pending.chatModel;
      }
    }
    if (pending && pending.imageModel) {
      var image = root.querySelector("#dragon-ai-image-model");
      if (image) {
        image.value = pending.imageModel;
      }
    }
    function post(ifMissing) {
      var chatModel = root.querySelector("#dragon-ai-chat-model").value;
      var imageModel = root.querySelector("#dragon-ai-image-model").value;
      setNote("Linking the selected models...");
      return api("/dragon-ai-api/models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat: chatModel,
          image: imageModel,
          ifMissing: !!ifMissing,
          provider: "xai",
        }),
      }).then(function (data) {
        if (!data || data.ok !== true) {
          setNote((data && (data.error || data.message)) || "Could not save models.");
          return false;
        }
        markSaved();
        hide(root);
        return true;
      }).catch(function (err) {
        setNote("Could not save models. " + err);
        return false;
      });
    }
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      post(false);
    });
    root.querySelector("#dragon-ai-models-skip").addEventListener("click", function () {
      post(true);
    });
  }

  function boot() {
    if (saved()) {
      return;
    }
    var tries = 0;
    function decide() {
      if (saved() || nativeProviderSetupVisible()) {
        var existing = document.getElementById(ROOT_ID);
        if (existing) {
          hide(existing);
        }
        return;
      }
      tries += 1;
      if (tries < 16) {
        setTimeout(decide, 250);
        return;
      }
      api("/dragon-ai-api/models", { method: "GET" })
        .then(function (data) {
          if (nativeProviderSetupVisible()) {
            return;
          }
          if (data && data.saved === true) {
            markSaved();
            return;
          }
          show(data || {});
        })
        .catch(function () {
          if (!nativeProviderSetupVisible()) {
            show({});
          }
        });
    }
    decide();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
