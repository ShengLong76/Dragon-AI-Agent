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
| Background | `#1C1C20` |
| Panel | `#282830` |
| Text | `#F0F0F5` |
| Muted text | `#A0A0AA` |
| Wordmark face | Syne 700 |

Full token table and skill-vs-override notes: `design-system/dragon-ai-agent/` (`MASTER.md` = raw generator output, `pages/desktop-client.md` = what we ship).

## What changes for James

- Empty-state **DRAGON AI AGENT** still Syne 700, now on the shared tokens (foreground, tracking), **in front of** a larger unboxed navy dragon.
- Composer **Give Dragon AI a task** keeps the copy; focus-visible uses the crimson ring.
- Settings / About stay **Dragon AI Agent**.
- Setup wizard colors stay the same RGB values, now named as this system.
- Product mark is James’s front-facing navy low-poly dragon (coiled neck, same-color horns, red eyes, no boxed background) on empty state, wizard, and shortcuts.
- Sidebar under Embedded Linux lists **Personal Assistant** only on a fresh install. The built-in default Hermes agent is **excluded** from the product (purged from `hermes\\profiles\\default` and `hermes`, never redeployed). CSS hide of `[data-roster-key$="::default"]` stays as a backstop so a leftover reserved row stays hidden. Real Estate / Marketing / Trading arrive only when chosen from Teams (or import).
- Sidebar header above SESSIONS / BOTS shows the navy dragon + **Dragon AI** (accessible name **Dragon AI Agent**). The mark is a fixed 32px transparent SVG (no plate / no red border), matched to the Teams button height. Narrowing the rail wraps Teams below the logo instead of shrinking or clipping the lockup.
- Imported / deployed bot groups file into a named BOTS section labeled with the pack display name. They are not left under UNASSIGNED.
- First-run setup has a **Models** step (after Welcome) for default chat LLM + default image LLM. Product defaults are Grok (xAI) + Grok Imagine. Design: `docs/airmaze/FIRST_RUN_MODELS.md`.
- Opening Dragon AI Agent starts Docker Desktop in the **tray** when the engine is down (no Containers dashboard). Design: `docs/airmaze/DOCKER_LAUNCH.md`.

## What does not change

Hermes.exe, `app.asar`, Bot Screen gateway, tokens, ports, container names, and license attribution. First-run model setup does not invent a new OAuth flow.
