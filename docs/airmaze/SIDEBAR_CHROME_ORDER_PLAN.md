# Plan — Sidebar chrome order (logo + Teams Marketplace above Sessions/Bots)

After `docs/airmaze/SIDEBAR_HOST.md` (design sign-off). Tests first. Packaging overlay only. No `Hermes.exe` rebuild. James / Cos merge.

## James

UltraDragon still shows **SESSIONS | BOTS** first (or overlapping the lockup). Annotation: move the Dragon AI logo and **Teams Marketplace** button **above** those tabs and push everything else down.

PR #20 kept the overlay *off* BOTS by pinning a body overlay at `top: 96px`. That reserved height *below* the native strip, so the tabs stayed visually first. Clearance-as-sibling of a horizontal tab row can also sit *beside* the tabs instead of above them.

## Desired order (top → bottom)

1. Dragon AI logo (+ name lockup)
2. Teams Marketplace button
3. Native Hermes **SESSIONS / BOTS** strip
4. Search, bot list, and the rest of the rail

## Tasks

1. **Docs** — this file + rewrite `SIDEBAR_HOST.md`. Correct PRODUCT / TEAMS / DESIGN / BRANDING notes that still say the overlay sits *below* the tabs. `CHANGELOG.md`.
2. **Tests first** — `Test-DesktopBranding.py` / `Test-TeamsPicker.py` / overlay self-test:
   - Documented DOM order string: `lockup → Teams Marketplace → Sessions/Bots`
   - In-flow rail column (`findInFlowColumn` + `[data-dragon-ai-sidebar-chrome]`) preferred
   - Fixed overlay fallback still exists, but default `top` is the **reserved rail top** (`0` / clearance box), never `96` (that leaves SESSIONS first) and never `48` (covers BOTS)
   - Clearance / chrome **height** still ≥ `96` so stacked Marketplace fits above the strip
   - Label stays **Teams Marketplace**; no crimson lockup border; 16px name remaps stay
   - BOTS stays clickable (`pointer-events: none` on the fixed host)
   - Do not treat `sidebar-wrapper` as a column host
3. **Overlay** — `sidebar-header.js` / `teams-picker.js` / `dragon-ui.css`:
   - Column slots first (unchanged)
   - Else prepend in-flow chrome to the Sessions-zone column (ancestor of the tab strip that also holds roster/body; skip horizontal tab rows)
   - Else body fixed overlay pinned into a first-child clearance spacer on that column
4. **Self-review + draft PR** against `main`. Do not merge from the agent.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-TeamsPicker.py
```
