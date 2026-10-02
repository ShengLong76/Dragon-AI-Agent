# Syne — empty-state wordmark face

**Family:** Syne  
**License:** SIL Open Font License 1.1 (`OFL.txt`)  
**Authors:** The Syne Project Authors — https://gitlab.com/bonjour-monde/fonderie/syne-typeface

This package does **not** vendor Universal Sans, Gotham, or any proprietary Tesla face, and does not claim to ship them.

The upstream Hermes empty-state wordmark is the **Collapse** display face (`font-family: Collapse` in `apps/desktop/src/styles.css`): a high-contrast bold with thick/thin strokes. That is the red-boxed “DRAGON AI AGENT” lettering.

Syne is a free OFL geometric sans (variable, 400–800). The overlay uses **weight 700** on the wordmark, then the same family on composer and the product chrome it already touches. Files are registered as both `Syne` and `Collapse`, and unpacked `.wordmark` `font-family` is rewritten so UltraDragon does not keep drawing Collapse-Bold.

`dragon-ui.css` also ships the applied design-system tokens (AI-Native UI, dark surfaces, crimson `#C41E3A`) and Grok Bot type/contrast (`16px` / `1.55` body, muted `#C4C4CE`). The chat transcript pane is black with blue-shade user/assistant bubbles (`docs/airmaze/CHAT_BUBBLES.md`). See `docs/airmaze/DESIGN.md` and `design-system/dragon-ai-agent/pages/desktop-client.md`. Do not add Inter or a second family.

`sidebar-header.js` and `teams-picker.js` are the prebuilt overlay injects. `Apply-DesktopBranding.ps1` copies them into unpacked `dist/dragon-ai-branding/` even when Python is not on PATH. The sidebar lockup is a transparent 56px SVG (1.75×; `border:0`) to the right of hide-sidebar, with reserved padding/gap so no control overlays the mark. Order is lockup → **blue Teams Marketplace** → Sessions / Bots. Column hosts first; else in-flow `data-dragon-ai-sidebar-chrome` on the Sessions-zone column; else a body overlay (`data-dragon-ai-sidebar-fixed`) in a first-child clearance spacer above Sessions / Bots (never cover those tabs). The control label is the full **Teams Marketplace** string. Clicking it opens a roomy centered popup (not a dropdown) with a 4-column seat-card grid. Marketplace stacks below the logo on a narrow rail (`@container`) or overlay (`@media (max-width: 1100px)`). Sidebar bot names and middle session/agent names share 16px body. Composer chrome has no persistent crimson island; **Start conversation** sits on the right-side action.
