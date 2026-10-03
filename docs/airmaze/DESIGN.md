# Dragon AI Agent — desktop chrome design

Short design for the surfaces this repo actually controls. Generated from the open-source **UI UX Pro Max** skill, then adapted to the launch-time overlay (not a rebuilt Electron app).

## Product

**Dragon AI Agent** is a desktop AI agent client. This tree packages and launches upstream `Hermes.exe`. James sees Dragon copy and Syne on the empty state, composer, and Settings/About because a launch overlay rewrites the unpacked renderer. Bot Screen stays on `127.0.0.1:8650` with token `dragon-local`.

## Direction (from the skill)

Query: `AI chatbot platform desktop agent dark` (variance 4, motion 2, density 6).

- **Style:** AI-Native UI — conversational, ambient, **minimal chrome**, single accent.
- **Not applied as a landing page:** the skill’s “Product Demo + Features” pattern is for marketing sites. This is an existing desktop chat client.
- **Not applied as catalog purple / Inter:** the skill’s AI/Chatbot row is lavender + Inter. That fights the locked **Syne** wordmark and the existing dark wizard. The same skill’s AI-Native style says *neutral + single accent*; its developer-tool / OLED rows say dark surfaces.

## Applied look

Dark, quiet chrome. Composer focus uses crimson `#C41E3A`. Type is **Syne** (OFL). Wordmark stays weight **700**. Composer and settings use the same family. Focus rings are visible. Motion is optional and off under `prefers-reduced-motion`. No Universal Sans, Gotham, Tesla faces, Inter webfont, or new UI framework.

**Mark:** James’s navy low-poly dragon — front-facing, coiled neck, few large facets, horns the same navy as the body (`#314A73`), red eyes (`#C41E3A`). No gold horns, no copper ring, not a side profile, **no boxed black plate**. Source image cropped to `branding/dragon-ai-agent-logo.png` with the field punched so the mark sits on the dark window; SVG companion is `branding/dragon-ai-agent-logo.svg`. The overlay pins a **larger** PNG behind the empty-state wordmark (`min(22rem, 70%)` of the intro pane, `overflow: visible` so a parent clip cannot crop it back into a box); the **DRAGON AI AGENT** wordmark sits in front of that mark. Wizard and shortcuts use the same unboxed PNG/ICO.

| Token | Value |
|-------|--------|
| Accent / primary / focus ring | `#C41E3A` |
| Header lockup band (WinForms) | `#2563EB` (same as Teams Marketplace) |
| Background | `#1C1C20` |
| Panel | `#282830` |
| Text | `#F0F0F5` |
| Muted text | `#C4C4CE` (was `#A0A0AA`; Grok Bot contrast) |
| Body / chat / composer | `16px` / `1.55` |
| Sidebar chrome | `14px` / `1.4` |
| Wordmark face | Syne 700 |
| Chat pane | `#000000` (transcript only; chrome stays `#1C1C20`) |
| User bubble | `#2563EB` / `#FFFFFF` |
| Assistant bubble | `#17345A` / `#F0F0F5` |

### Type and contrast (Grok Bot parity)

James: Hermes desktop type is too small and low-contrast next to Cursor Grok Bot. Upstream `apps/desktop/src/styles.css` sets `body` and `--conversation-text-base-size` to **0.8125rem (13px)** and `--ui-text-tertiary` to a **54%** mix of `--ui-base`. That fails the skill’s 4.5:1 normal-text bar for secondary chrome.

The overlay (still Syne + crimson, no rebuild) remaps those Hermes variables and sets explicit rules on sidebar, chat slots, composer, and the Teams picker so body copy is **16px / 1.55** with opaque `#F0F0F5` on `#1C1C20`. Muted chrome is `#C4C4CE`, not a transparent grey. Tray-icon contain-fit is untouched.

### Transcript bubbles (Grok Bot feel)

James: the transcript must not stay flat text on crimson panels. Match Grok Bot’s conversational cards — black pane, rounded user vs assistant bubbles — with **blue-shade** fills. Overlay remaps Hermes `--dt-user-bubble` on the thread and paints `[data-slot="aui_assistant-message-content"]`. Chrome / logo / focus stay crimson. Design: `docs/airmaze/CHAT_BUBBLES.md`.

Full token table and skill-vs-override notes: `design-system/dragon-ai-agent/` (`MASTER.md` = raw generator output, `pages/desktop-client.md` = what we ship).

## What changes for James

- Empty-state **DRAGON AI AGENT** still Syne 700, now on the shared tokens (foreground, tracking), **in front of** a larger unboxed navy dragon.
- Sidebar, chat, composer, and the in-app Teams picker use Grok Bot–sized type (16px body, 14px chrome) and stronger dark contrast (`#F0F0F5` / `#C4C4CE` on `#1C1C20`).
- Composer **Give Dragon AI a task** keeps the copy; focus-visible uses the crimson ring.
- Settings / About stay **Dragon AI Agent**.
- Setup wizard / launch-status / WinForms Teams header band behind the dragon + **Dragon AI Agent** is Marketplace blue `#2563EB`. Primary buttons stay crimson. Design: `docs/airmaze/HEADER_LOCKUP_BLUE.md`.
- Product mark is James’s front-facing navy low-poly dragon (coiled neck, same-color horns, red eyes, no boxed background) on empty state, wizard, and shortcuts.
- Sidebar under Embedded Linux lists **Personal Assistant** only on a fresh install. The built-in default Hermes agent is **excluded** from the product (purged from `hermes\\profiles\\default` and `hermes`, never redeployed). CSS hide of `[data-roster-key$="::default"]` stays as a backstop so a leftover reserved row stays hidden. Real Estate / Marketing / Trading arrive only when chosen from Teams (or import).
- Sidebar header above SESSIONS / BOTS shows the navy dragon + **Dragon AI** (accessible name **Dragon AI Agent**) and a **blue Teams Marketplace** control under the logo. The mark is a fixed **56px** transparent SVG (1.75× the prior 32px; no plate / no red border) with reserved padding/gap so no control overlays it. The lockup sits to the **right of hide-sidebar**. Order is lockup → Teams Marketplace → Sessions / Bots. When header/inner are missing, prefer in-flow chrome on the Sessions-zone column; else a body overlay in a first-child clearance spacer **above** those tabs so BOTS stays clickable (`docs/airmaze/SIDEBAR_HOST.md`, `docs/airmaze/PACKAGING_CHROME.md`, `docs/airmaze/SIDEBAR_LOGO_PLAN.md`).
- Composer has no persistent crimson outline. GPT | Grok pills are gone. A right-side **waveform** opens the Grok-Bot floating capsule **at the top of the chat pane** (`Talk with Grok` duplex; narrower/taller pill). Gear opens Voice settings (voice, speed). Focus-visible stays crimson.
- Sidebar bot names (Personal Assistant) and middle session/agent names (Dragon AI Tester) share the **16px** body size. Hermes `0.8125rem` name chips are remapped so the two lists match.
- Imported / deployed bot groups file into a named BOTS section labeled with the pack display name. They are not left under UNASSIGNED.
- First-run setup has a **Models** step (after Welcome) for default chat LLM + default image LLM. Product defaults are Grok (xAI) + Grok Imagine. Design: `docs/airmaze/FIRST_RUN_MODELS.md`.
- Opening Dragon AI Agent starts Docker Desktop in the **tray** when the engine is down (no Containers dashboard). Design: `docs/airmaze/DOCKER_LAUNCH.md`.
- Dragon AI Agent Setup **owns Docker Desktop** on a clean PC (packaged installer or Setup-owned download; no docker.com-first step). Design: `docs/airmaze/DOCKER_INSTALL.md`.
- Product shortcut parse: tray `$patch` has one `openUIOnStartupDisabled` key; Hermes data dir is `$embeddedHome` / `-HermesHome` (never `$HOME`). Design: `docs/airmaze/WINDOWS_LAUNCH_PARSE.md`.
- **Teams Marketplace** opens a roomy centered popup (backdrop, per-team Install, Launch / Import / Export / Details → Install). Seats stay 4-column cards under each pack, with a left-side icon, a brief line, and hover/focus detail. Marketing SEO Specialist copy is seoagent.com. Design: `docs/airmaze/TEAMS_POPUP.md`, `docs/airmaze/TEAMS_SEAT_DESCRIPTIONS.md`.
- Voice conversation mode in Settings lists **Chained**, **Gpt-live**, and **Grok Voice**. GPT voice is unchanged (`gpt-live`). Grok Voice is additive overlay full duplex (`grok-voice-latest`). Chat-screen GPT | Grok pills are removed; the composer waveform hosts the capsule. Design: `docs/airmaze/VOICE.md`.
- The running-app / taskbar dragon is the **transparent sidebar mark**, contain-maxed into the Windows slot (no fixed pixel size, no copper badge rim). Apply copies that ICO **and** PNG onto the private `win-unpacked` tree (`icon.ico`, `icon.png`, `apple-touch-icon.png`) and refuses standalone Hermes. Design: `docs/airmaze/TRAY_ICON.md`, `docs/airmaze/DURABLE_BRANDING.md`.
- Chat transcript uses Grok-Bot conversational bubbles: **black** pane, user `#2563EB`, assistant `#17345A`. Syne + crimson chrome unchanged. Design: `docs/airmaze/CHAT_BUBBLES.md`.

## What does not change

Hermes.exe, `app.asar`, Bot Screen gateway, tokens, ports, container names, and license attribution. First-run model setup does not invent a new OAuth flow.
