# Syne — empty-state wordmark face

**Family:** Syne  
**License:** SIL Open Font License 1.1 (`OFL.txt`)  
**Authors:** The Syne Project Authors — https://gitlab.com/bonjour-monde/fonderie/syne-typeface

This package does **not** vendor Universal Sans, Gotham, or any proprietary Tesla face, and does not claim to ship them.

The upstream Hermes empty-state wordmark is the **Collapse** display face (`font-family: Collapse` in `apps/desktop/src/styles.css`): a high-contrast bold with thick/thin strokes. That is the red-boxed “DRAGON AI AGENT” lettering.

Syne is a free OFL geometric sans (variable, 400–800). The overlay uses **weight 700** on the wordmark, then the same family on composer and the product chrome it already touches. Files are registered as both `Syne` and `Collapse`, and unpacked `.wordmark` `font-family` is rewritten so UltraDragon does not keep drawing Collapse-Bold.

`dragon-ui.css` also ships the applied design-system tokens (AI-Native UI, dark surfaces, crimson `#C41E3A`) and Grok Bot type/contrast (`16px` / `1.55` body, muted `#C4C4CE`). See `docs/airmaze/DESIGN.md` and `design-system/dragon-ai-agent/pages/desktop-client.md`. Do not add Inter or a second family.

`sidebar-header.js` and `teams-picker.js` are the prebuilt overlay injects. `Apply-DesktopBranding.ps1` copies them into unpacked `dist/dragon-ai-branding/` even when Python is not on PATH. The sidebar lockup is a transparent 32px SVG (`border:0`). Column hosts first; else a body overlay (`data-dragon-ai-sidebar-fixed`) below Sessions / Bots. The control label is **Teams Marketplace**. Marketplace wraps below the logo on a narrow rail (`@container`) or overlay (`@media (max-width: 1100px)`).
