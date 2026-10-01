# Sidebar lockup host fallback

Short design after the UltraDragon fix that mounted. Brand + Teams Marketplace scripts were in unpacked `index.html` but never painted. Voice inject did. Live Hermes has no `[data-slot="sidebar-header"]` / `sidebar-inner` — only `sidebar-wrapper`, and that node is the **full app shell**, not the left rail.

## Why header/inner never appear

Upstream still *defines* those slots in `sidebar.tsx`. `ContribController` only mounts `SidebarProvider` (`data-slot="sidebar-wrapper"`, `--sidebar-width: 100%`, `flex-col`). Sessions / Bots live in the layout-tree pane. Scripts that wait on header/inner return forever.

## Do

`sidebar-header.js` / `teams-picker.js`:

1. **Column hosts first:** `sidebar-header`, `data-sidebar="header"`, `sidebar-inner`, `sidebar-container`, `sidebar`. Prepend the lockup. Keep `@container` wrap so Marketplace drops below the logo when that rail is narrow.
2. **Else body fixed overlay:** `[data-dragon-ai-sidebar-fixed]` on `document.body`. Park it **below** the Sessions / Bots strip (measure the Bots chip, default `top: 48px`) so those tabs stay visible and clickable. Width rules: `16rem` min/max on the host and the row.
3. **Skip `sidebar-wrapper` as a column.** It is the window shell. Treating it as a rail makes a full-width top bar and collapses the lockup.

`dragon-ui.css`:

- Real slots keep `container-type` + `@container (max-width: 14rem)` wrap.
- **Do not** put `container-type` on the fixed row (it collapses to ~24px).
- Overlay wrap: `@media (max-width: 1100px)`.

## Keep (visual)

- No crimson lockup border (`border: 0`)
- Transparent 32px SVG, Syne 700 **Dragon AI**
- User-visible control label **Teams Marketplace** (not “Teams”)
- Teams crimson accent (`#C41E3A` ring / primary)
- Wrap when a real sidebar column exists

Do not restyle Bot Screen. No `Hermes.exe` rebuild. No `app.asar` rewrite.

UI UX Pro Max: decorative logo `aria-hidden`; wordmark nowrap + ellipsis; Marketplace is the wrap collection (`flex-wrap`, not a clipped row); overlay z-index 40 (dialog 80). Sticky overlay must not cover Sessions / Bots hit targets.

## Verify

```bash
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-TeamsPicker.py
```

UltraDragon: close `Hermes.exe`, apply branding. Lockup + **Teams Marketplace** mount on the body overlay; Sessions / Bots stay clickable.
