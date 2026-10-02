# Packaging overlay chrome — Marketplace label + composer

Short design after James’s UltraDragon annotation (logo + truncated **Teams Marke**, crimson composer island). Packaging overlay only. No `Hermes.exe` rebuild. No wholesale `app.asar` rewrite. Stacks on / supersedes PR #22 sidebar order (`lockup → Teams Marketplace → Sessions/Bots`).

## 1) Teams Marketplace under the logo, full label

**Order (top → bottom):** Dragon AI lockup → **Teams Marketplace** (entire words) → SESSIONS / BOTS.

James still sees **Teams Marke** beside the logo. That is Compact Label Overflow (UI UX Pro Max): an essential chip clipped mid-word. The full string is known and required — do not ellipsize it. The wrap collection is the **column** (logo row, then the button), not a clipped horizontal pill.

### Do

- Column stack on `[data-dragon-ai-sidebar-row]` / `[data-dragon-ai-sidebar-chrome]`. Button `width: 100%` under the 56px mark (1.75×). Lockup sits to the right of hide-sidebar.
- Keep the label **Teams Marketplace**. Prefer one line (`white-space: nowrap`) on a ≥16rem rail.
- If the rail is narrower than the string, wrap at the word (`Teams` / `Marketplace`) — never `text-overflow: ellipsis`, never mid-word clip.
- `overflow: visible` on the button and its row. Drop `min-width: max-content` (that overflows a narrow host and Hermes `truncate` then paints **Teams Marke**).
- Fixed overlay width is at least `16rem` (`Math.max(256, …)`). Do not shrink the host to a title-bar sliver.
- Keep: BOTS clickable, no crimson lockup border, 16px name remaps, `findInFlowColumn` / `top: 0` from PR #22.
- **Blue Marketplace button only:** `[data-dragon-ai-teams-open]` is filled `#2563EB` with `#FFFFFF` text. Hover `#3B82F6`, active `#1D4ED8`. Do not retint `--color-primary` / the dragon / Syne.

### Logo clearance (no overlay)

Nothing — Marketplace, Sessions/Bots, or other icons — may paint on top of the 56px dragon. The lockup is a reserved box: `flex: 0 0 auto`, `isolation: isolate`, `z-index: 2`, `padding-bottom: 8px`, row `gap: 12px` (`--dragon-logo-clearance`). Marketplace sits in normal flow under that box (`z-index: 1`). Logo size is `56px` (1.75× the prior 32px). Stamp: `dragon-ai-logo-clearance:1`, `dragon-ai-logo-175:1`.

Host fallback remains `docs/airmaze/SIDEBAR_HOST.md`. Stamps: `dragon-ai-marketplace-label:1`, `dragon-ai-marketplace-blue:1`.

## 2) Composer chrome — no red island; start conversation on the action

**Annotation:** remove the crimson outline around “Give Dragon AI a task”, VOICE / GPT / Grok, and Talk with Grok. Integrate **start conversation** into the right-side composer action / talk control.

`--color-ring: #C41E3A` on `:root` plus a crimson **Talk with Grok** border made a persistent frame. Focus Appearance still needs a 2px ring on the **textbox and pills**, not a wrapper island.

### Do

- Strip persistent outline / box-shadow / tw-ring on `[data-slot="aui_composer"]`, `[data-slot="composer"]`, `[data-dragon-voice-provider]`, and the action cluster. Composer border stays `--color-border`.
- Keep `:focus-visible` on the textbox, GPT/Grok, and the talk control (`2px solid #C41E3A`, offset 2px). Selected GPT/Grok fill stays crimson.
- Mount GPT | Grok as borderless toolbar chrome inside the composer (`data-dragon-ai-composer-chrome`).
- Move Talk into `[data-dragon-ai-composer-action]` immediately before the native right-side action (voice / mic / last composer button). Idle visible label **Start conversation**; accessible name includes **Talk with Grok**. Live: **Stop Grok**. No separate crimson-bordered island.
- Do not hijack Send. GPT still uses the Hermes mic. Grok duplex stays overlay `wss://api.x.ai/v1/realtime?model=grok-voice-latest`.

Stamp: `dragon-ai-composer-chrome:1`. Voice contract: `docs/airmaze/VOICE.md`.

## Keep

Syne 700, navy 56px SVG (1.75×), `#C41E3A` accent on **focus and selected state only**, 16px / 1.55 body, Bot Screen `:8650` / `dragon-local`. `prefers-reduced-motion` unchanged.
