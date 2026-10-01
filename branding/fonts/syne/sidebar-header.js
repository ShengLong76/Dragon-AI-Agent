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
  function mount() {
    var host = document.querySelector('[data-slot="sidebar-header"]')
      || document.querySelector('[data-slot="sidebar-inner"]');
    if (!host) return;
    var existing = host.querySelector("[data-dragon-ai-sidebar-brand]");
    if (existing) {
      pinWrap(existing);
      var old = existing.querySelector("img");
      if (old) pinLogo(old);
      return;
    }
    var row = document.createElement("div");
    row.setAttribute("data-dragon-ai-sidebar-row", "true");
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
