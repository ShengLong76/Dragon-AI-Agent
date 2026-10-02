# Plan — Marketplace label + composer chrome

After `docs/airmaze/PACKAGING_CHROME.md`. Tests first. Packaging overlay only. No `Hermes.exe` rebuild. Draft PR; do not merge. Base: latest `main`. Stacks on PR #22 (`abf8f1ab`) so one PR carries sidebar order + these two UltraDragon fixes.

## James

1. **Teams Marketplace below logo** — arrow on truncated **Teams Marke**. Full label must sit under the lockup, then Sessions/Bots. Button is **filled blue**.
2. **Composer** — remove the red border around the chat box and the GPT/Grok pills. Put a **waveform** on the right-side action that opens the Grok-Bot capsule.
3. **Logo clearance** — no control or icon overlays the 32px dragon. Reserved padding/gap under the lockup. BOTS stays clickable.

## Tasks

1. **Docs** — this file + `PACKAGING_CHROME.md`. Update `SIDEBAR_HOST.md`, `VOICE.md`, `DESIGN.md`, `pages/desktop-client.md`, `CHANGELOG.md`.
2. **Tests first** — `Test-DesktopBranding.py` / `Test-TeamsPicker.py` / `Test-VoiceChat.py` / overlay self-test:
   - Order stamp `lockup → Teams Marketplace → Sessions/Bots` (PR #22) stays
   - `dragon-ai-marketplace-label:1`; no `min-width: max-content` on the Teams root; no ellipsis on `[data-dragon-ai-teams-open]`; `overflow: visible`; word-boundary wrap fallback; overlay `Math.max(256`
   - `dragon-ai-marketplace-blue:1`; `[data-dragon-ai-teams-open]` background `#2563eb` / `#ffffff` (not `--color-primary`)
   - `dragon-ai-logo-clearance:1`; lockup `flex: 0 0 auto` + `--dragon-logo-clearance: 12px`; logo stays `32px`; Marketplace `z-index` below the lockup
   - BOTS clickable; no crimson lockup border; 16px name remaps
   - `dragon-ai-composer-chrome:1`; no persistent crimson outline on composer / voice / talk; Talk has no `border: 1px solid` primary
   - Voice JS has `data-dragon-voice-trigger`, `findComposerAction`, `data-dragon-ai-composer-action`; top-docked floating capsule (`dockWidget` / `findChatColumn`) + gear Voice settings + official xAI duplex. No GPT | Grok pills.
   - `:focus-visible` rings stay
3. **Overlay** — `dragon-ui.css`, `sidebar-header.js`, `teams-picker.js`, `dragon-voice-selector.js`. Apply-DesktopBranding verifies the new stamps.
4. **Self-review + draft PR** against `main`. Note supersedes #22. Do not merge.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-DesktopBranding.py
python3 scripts/airmaze/Test-TeamsPicker.py
python3 scripts/airmaze/Test-VoiceChat.py
```
