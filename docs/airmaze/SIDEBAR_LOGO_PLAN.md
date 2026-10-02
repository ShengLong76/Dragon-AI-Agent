# Plan — Sidebar lockup 1.75×, right of hide-sidebar

After James’s UltraDragon Bot Screen markup (red box on the top-left Dragon AI mark). Packaging overlay only. No `Hermes.exe` rebuild. No `app.asar` rewrite. James / Cos merge.

## James

Increase the Dragon AI logo/wordmark by **75%** (new size ≈ **1.75×** the current 32px mark → **56px**; Syne 700 name **16px → 28px**) and **move it to the right of the hide-sidebar icon**.

Hide-sidebar is Hermes titlebar chrome (`TitlebarTool` id `sidebar`, labels **Hide sidebar** / **Show sidebar**, or shadcn `[data-sidebar="trigger"]`). The lockup currently leads the rail and can sit left of / across that control. Desired header row: hide-sidebar → larger lockup. **Teams Marketplace** stays under the logo area (column stack). Do not cover BOTS.

## Keep

- Syne 700, crimson `#C41E3A` on focus/selected only
- Transparent SVG mark; no red border / plate
- Blue Teams Marketplace button (`#2563EB` / `#FFFFFF`)
- Order stamp: `lockup → Teams Marketplace → Sessions/Bots`
- Host fallback from `docs/airmaze/SIDEBAR_HOST.md`
- Bot Screen `:8650` / `dragon-local`

## Tasks

1. **Docs** — this file + `DESIGN.md` / `SIDEBAR_HOST.md` / `PACKAGING_CHROME.md` / `BRANDING.md` / `CHANGELOG.md`.
2. **Tests first** — `Test-DesktopBranding.py` / `Test-TeamsPicker.py` / overlay self-test:
   - Stamp `dragon-ai-logo-175:1`; logo `56px` (`--dragon-sidebar-logo-size`); lockup wordmark `28px`
   - `findHideSidebar` + place lockup as the next sibling of `[data-dragon-ai-hide-sidebar]`
   - Marketplace still under the logo area; blue button; no crimson lockup border
   - Clearance still ≥96px so stacked Marketplace does not cover BOTS
   - Teams control height stays `32px` (not scaled)
3. **Overlay** — `sidebar-header.js` / `dragon-ui.css`. Apply-DesktopBranding verifies the new stamp.
4. **Draft PR** against `main`. Do not merge from the agent.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-TeamsPicker.py
```
