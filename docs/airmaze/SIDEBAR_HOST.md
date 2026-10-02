# Sidebar lockup host (chrome order)

Design sign-off after James’s UltraDragon annotation: the Dragon AI lockup and **Teams Marketplace** must sit **above** the native Sessions / Bots strip, and the rest of the rail must move down. Packaging overlay only. No `Hermes.exe` rebuild. No wholesale `app.asar` rewrite.

## Expected DOM / visual order (top → bottom)

1. `[data-dragon-ai-sidebar-brand]` — Dragon AI logo + name lockup
2. `[data-dragon-ai-teams-root]` — **Teams Marketplace** (not “Teams”)
3. Native Hermes **SESSIONS / BOTS** tab strip
4. Search, bot list, and the rest of the left rail

Stamp: `lockup → Teams Marketplace → Sessions/Bots`

## Why header/inner never appear

Upstream still *defines* `sidebar-header` / `sidebar-inner` in `sidebar.tsx`. `ContribController` only mounts `SidebarProvider` (`data-slot="sidebar-wrapper"`, `--sidebar-width: 100%`, `flex-col`). Sessions / Bots live in the layout-tree **sessions zone** (`TreeGroup`: header strip + pane body). Scripts that wait on header/inner return forever.

PR #20 pinned a body overlay at `top: 96px` so it would not cover BOTS. That placed the lockup *below* the native strip (or overlapping the list). A clearance spacer inserted as a sibling of a **horizontal** SESSIONS|BOTS row can also sit beside the tabs. James still sees SESSIONS|BOTS first.

## Do

`sidebar-header.js` / `teams-picker.js`:

1. **Column hosts first:** `sidebar-header`, `data-sidebar="header"`, `sidebar-inner`, `sidebar-container`, `sidebar`. Prepend the lockup. Keep `@container` wrap so Marketplace drops below the logo when that rail is narrow.
2. **Else in-flow rail column:** `findInFlowColumn` walks from the Sessions/Bots strip to the zone that also holds the pane body / `[data-slot="bots-roster"]`. Skip horizontal tab rows (`looksHorizontalChrome`) and skip `sidebar-wrapper` / `body` (`isAppShell`). Prepend `[data-dragon-ai-sidebar-chrome]` as the first child (`order: -1`). Mount the lockup row + Teams Marketplace **inside** that chrome so the native strip and everything below shift down. Prefer this over a fixed overlay.
3. **Else body fixed overlay:** `[data-dragon-ai-sidebar-fixed]` on `document.body`. Insert `[data-dragon-ai-sidebar-clearance]` as the **first child** of that same column (not as a sibling inside the tab row). Pin the overlay to the **clearance box top** (default CSS/JS `top: 0`, never `top: 96px` — that leaves SESSIONS first — and never `top: 48px` on the tab). `lockupHeight` / chrome / clearance **min-height 96** so stacked Marketplace fits above the strip. Host `pointer-events: none`; only the lockup row and Marketplace button take clicks. If the strip is `sticky` / `absolute` / `fixed`, bump its `top` by that height once.
4. **Skip `sidebar-wrapper` as a column.** It is the window shell.

`dragon-ui.css`:

- Real slots keep `container-type` + `@container (max-width: 14rem)` wrap.
- **Do not** put `container-type` on the fixed row (it collapses to ~24px).
- Overlay wrap: `@media (max-width: 1100px)`.
- In-flow chrome: column stack, `min-height: 96px`, `order: -1`.

## Keep (visual)

- No crimson lockup border (`border: 0`)
- Transparent 32px SVG, Syne 700 **Dragon AI**
- User-visible control label **Teams Marketplace** (not “Teams”)
- Filled **blue** Marketplace button (`[data-dragon-ai-teams-open]`, `#2563EB` / `#FFFFFF`). Crimson stays on focus/selected chrome elsewhere
- Logo clearance: reserved 32px mark, `isolation: isolate`, `padding-bottom: 8px`, row `gap: 12px` so Marketplace / Sessions / Bots never overlay the dragon
- Teams crimson accent (`#C41E3A` ring / primary) except the blue Marketplace control
- Full **Teams Marketplace** label (no mid-word clip). Column stack under the logo
- Sidebar bot names and middle session/agent names share **16px** body

Do not restyle Bot Screen. No `Hermes.exe` rebuild. No `app.asar` rewrite.

UI UX Pro Max: decorative logo `aria-hidden`; wordmark nowrap + ellipsis; Marketplace is the wrap collection (column under the logo, full label, no mid-word clip); overlay z-index 40 (dialog 80). Focus Not Obscured — sticky overlay must not cover Sessions / Bots hit targets (`pointer-events: none` on the fixed host). Logo clearance keeps controls off the 32px mark. See `docs/airmaze/PACKAGING_CHROME.md`.

## Verify

```bash
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-TeamsPicker.py
```

UltraDragon: close `Hermes.exe`, apply branding. Order is lockup → **Teams Marketplace** → Sessions / Bots. BOTS stays clickable.
