(function () {
  const statusEl = document.getElementById("status");

  function setStatus(text) {
    if (statusEl) {
      statusEl.textContent = text || "";
    }
  }

  function reportLaunch(result) {
    const ok = !!(result && result.ok);
    const err = (result && (result.error || result.message)) || "";
    setStatus(ok ? (result.message || "Launch started.") : (err || "Launch produced no result."));
    return result || { ok: false, error: "empty-launch-result" };
  }

  async function launch() {
    setStatus("Opening the desktop chat screen...");
    try {
      const res = await fetch("/api/launch", { method: "POST" });
      const data = await res.json();
      if (!data || typeof data.ok !== "boolean") {
        return reportLaunch({ ok: false, error: "Launch returned no result." });
      }
      if (data.ok) {
        window.location.reload();
      }
      return reportLaunch(data);
    } catch (err) {
      return reportLaunch({ ok: false, error: "Launch failed. " + err });
    }
  }

  async function waitForDesktopWebUI() {
    const deadline = Date.now() + 90000;
    while (Date.now() < deadline) {
      try {
        const res = await fetch("/dragon-ai-api/desktop-ui", { cache: "no-store" });
        const data = await res.json();
        if (data && data.headless) {
          setStatus("The desktop chat screen returned the headless web UI disabled page. Launch failed.");
          return reportLaunch({ ok: false, error: "Launch refused the headless web UI disabled page." });
        }
        if (data && data.ok) {
          window.location.reload();
          return reportLaunch({ ok: true, message: "Desktop chat screen is ready." });
        }
      } catch (_err) {}
      await new Promise(function (resolve) { setTimeout(resolve, 1500); });
    }
    setStatus("The desktop chat screen did not become ready.");
    return reportLaunch({ ok: false, error: "desktop web UI is not ready" });
  }

  window.reportLaunch = reportLaunch;
  window.launch = launch;

  if (document.body && document.body.getAttribute("data-dragon-ai-loader")) {
    waitForDesktopWebUI();
  }
})();
