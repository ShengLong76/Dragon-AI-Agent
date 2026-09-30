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

**Mark:** James’s navy low-poly dragon — front-facing, coiled neck, few large facets, horns the same navy as the body (`#314A73`), red eyes (`#C41E3A`). No gold horns, no copper ring, not a side profile. Source image cropped to `branding/dragon-ai-agent-logo.png`; SVG companion is `branding/dragon-ai-agent-logo.svg`. The overlay pins the PNG on the empty-state intro; wizard and shortcuts use the PNG/ICO.

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

- Empty-state **DRAGON AI AGENT** still Syne 700, now on the shared tokens (foreground, tracking).
- Composer **Give Dragon AI a task** keeps the copy; focus-visible uses the crimson ring.
- Settings / About stay **Dragon AI Agent**.
- Setup wizard colors stay the same RGB values, now named as this system.
- Product mark is James’s front-facing navy low-poly dragon (coiled neck, same-color horns, red eyes) on empty state, wizard, and shortcuts.

## What does not change

Hermes.exe, `app.asar`, Bot Screen gateway, tokens, ports, container names, and license attribution.
