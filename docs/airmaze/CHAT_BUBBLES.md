# Chat transcript bubbles (Grok Bot feel)

Short design after James’s Grok Bot screenshot. Packaging overlay only. No `Hermes.exe` rebuild. No `app.asar` rewrite. Bot Screen stays `127.0.0.1:8650` / `dragon-local`.

## Ask

Dragon AI Agent’s chat transcript should read like Cursor **Grok Bot**: a **black** conversation pane and **rounded user vs assistant bubbles**, not flat prose on crimson panels. Bubble fills are **shades of blue**. Syne + crimson stay on chrome / logo / focus / selected GPT|Grok.

## Applied look

Overlay CSS (`branding/fonts/syne/dragon-ui.css`) paints only the transcript surface:

| Token | Value | Role |
|-------|--------|------|
| `--dragon-chat-bg` | `#000000` | Thread / viewport / `[data-chat-surface]` |
| `--dragon-bubble-user` | `#2563EB` | Human bubble (Marketplace blue family) |
| `--dragon-bubble-user-fg` | `#FFFFFF` | 5.17:1 on the user fill |
| `--dragon-bubble-assistant` | `#17345A` | Assistant bubble (darker navy-blue) |
| `--dragon-bubble-assistant-fg` | `#F0F0F5` | 11.04:1 on the assistant fill |
| `--dragon-bubble-radius` | `18px` | Grok-like rounded cards |

Hermes already draws a user card via `--dt-user-bubble` (`.composer-human-message`). The overlay remaps that variable on the thread and adds an assistant card on `[data-slot="aui_assistant-message-content"]`. User bubbles shrink to content and sit on the right; assistant bubbles start on the left. Turn gap is `12px`. Long tokens use `overflow-wrap: anywhere` (UI UX Pro Max: long-token wrapping). Body measure stays under ~44rem (container width).

Do **not** set `--ui-chat-surface-background` on `:root` — Hermes paints `body` with that token, and sidebar chrome must stay `#1C1C20`.

## Skill notes

UI UX Pro Max `--design-system` (`AI chatbot dark conversational bubbles`) still resolves to **AI-Native UI**. Catalog purple / Inter are not shipped. Chat & Messaging product row says sender/receiver bubble contrast; OLED dark row says `#000000` pane. A first `chat message bubbles dark conversational` UX search returned **no database match**; the retry `conversation message layout` is what we applied (readable measure, no overflow-hidden clipping, wrap-anywhere).

## Keep

- Teams Marketplace filled blue, logo clearance, composer **waveform** → top-docked floating capsule, `:focus-visible` 2px `#C41E3A`
- HUD overlay (`[data-hud-shell]`) keeps transparent bubbles
- System / inter-agent notices stay compact captions, not blue cards
- Stamp: `dragon-ai-chat-bubbles:1`

Check: `python3 scripts/airmaze/Test-DesktopBranding.py`.
