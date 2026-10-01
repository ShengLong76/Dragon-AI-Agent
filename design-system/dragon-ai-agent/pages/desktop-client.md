# Desktop client override (Dragon AI Agent)

This file overrides `../MASTER.md` for chrome this packaging repo actually controls: the launch-time unpacked-renderer overlay (`branding/fonts/syne/dragon-ui.css`) and the WinForms onboarding wizard. It does **not** rebuild `Hermes.exe` or restyle Bot Screen.

## Why this override exists

UI UX Pro Max (`--design-system`, query `AI chatbot platform desktop agent dark`) recommended:

| Skill output | Why it is not applied as-is |
|--------------|-----------------------------|
| Style **AI-Native UI** | Keep. Conversational, minimal chrome, single accent. |
| Catalog palette **AI purple + lavender light** | Generic “AI slop” look. Clashes with the navy dragon mark and the wizard’s dark chrome. Skill **AI-Native UI** itself says *neutral + single accent*. |
| Typography **Inter** | Locked product face is **Syne** (OFL, wordmark 700), already bundled. Do not vendor Inter, Universal Sans, Gotham, or any Tesla face. |
| Pattern **Product Demo + Features** | Landing-page pattern. This repo overlays an existing desktop agent, not a marketing site. |
| Motion **GSAP scroll reveal** | No new framework. Overlay is CSS only. Honor `prefers-reduced-motion`. |

Developer-tool / OLED searches from the same skill (`developer tool IDE dark`, `dark mode cinematic desktop`) confirm dark surfaces for a desktop agent.

## Applied tokens

Reuse the wizard colors already in `Onboard-Wizard.ps1` so packaging chrome and the Electron overlay share one system.

| Role | Hex | CSS variable | WinForms |
|------|-----|--------------|----------|
| Primary / accent | `#C41E3A` | `--color-primary`, `--color-accent`, `--color-ring` | `196, 30, 58` |
| On primary | `#FFFFFF` | `--color-on-primary`, `--color-on-accent` | White |
| Secondary | `#C4A574` | `--color-secondary` | wizard header subtitle only; not used on the mark |
| Background | `#1C1C20` | `--color-background` | `28, 28, 32` |
| Foreground | `#F0F0F5` | `--color-foreground` | `240, 240, 245` |
| Card / panel | `#282830` | `--color-card` | `40, 40, 48` |
| Muted surface | `#32323A` | `--color-muted` | input `50, 50, 58` |
| Muted text | `#A0A0AA` | `--color-muted-foreground` | `160, 160, 170` |
| Border | `#50505A` | `--color-border` | `80, 80, 90` |
| Destructive | `#DC4646` | `--color-destructive` | `220, 70, 70` |
| Success | `#3CB45A` | `--color-ok` | `60, 180, 90` |
| Pending | `#C8A028` | `--color-pending` | `200, 160, 40` |

Text on `#1C1C20`: `#F0F0F5` and `#A0A0AA` both clear 4.5:1.

## Typography (locked)

- Wordmark: **Syne 700**, `letter-spacing: 0.04em`, color `--color-foreground`
- Composer / settings chrome the overlay already touches: same family, weight 400–600
- Register the files as `Collapse` as well so leftover upstream wordmark rules cannot reload Collapse-Bold

## Mark

James’s front-facing navy low-poly dragon (both eyes to the viewer, coiled neck). Large flat navy facets `#314A73` (horns the same navy); red eyes `#C41E3A`. **No boxed black plate** — the mark sits on the dark window. No gold, no copper ring, not a side profile. PNG is cropped from the attached mark with the field punched; SVG is the facet companion without a `<rect>` plate. Overlay copies both into `dragon-ai-branding/` and shows a **larger** PNG **behind** the empty-state wordmark (`min(22rem, 70%)` of the intro, `overflow: visible`, `z-index` so **DRAGON AI AGENT** is in front). Do not size the mark with `vw` (that includes the sidebar).

The Bots rail must not list the built-in default Hermes agent next to Personal Assistant. The product **excludes** that bot (purge leftover `default` / `hermes` folders). Overlay CSS hides `[data-roster-key$="::default"]` as a backstop; the string overlay blanks `return 'Hermes'`. **Personal Assistant** stays. Imported bot groups file into a named section, not UNASSIGNED.

The left-rail header above SESSIONS / BOTS is a brand lockup: decorative navy dragon (`aria-hidden`) + **Dragon AI** in Syne 700 (`#F0F0F5` on `#1C1C20`) + the **Teams Marketplace** control under the logo. The mark is transparent only (no red border, no plate) and a fixed `32px`. Wordmark ellipsizes. Marketplace type uses the 16px body contrast tokens. Accessible name **Dragon AI Agent**. Do not cover the BOTS tab hit targets.

The Teams dialog lists seats under each team as a **4-column CSS grid** (`repeat(4, 1fr)`; wrap, no empty filler cells). Each card is marketplace-style: a **32px** decorative SVG icon on the left (`aria-hidden`) beside title + brief. Brief (`description`) stays visible under the seat name; `descriptionDetail` is a hover/focus tooltip (`role="tooltip"`), not a native `title` and not the only path for the one-liner. Seat cards and the team Apply control share a **12px** radius and a dark-surface shadow. Apply is the team row. Seats are not nested buttons. Focus rings stay visible. Do not clamp essential seat names. Icons are navy/crimson low-poly SVGs in `branding/teams/`, not a runtime generate.

## Surfaces this overlay may style

- Empty-state wordmark, intro subtitle, and the front-facing dragon mark
- Sidebar header brand lockup (logo + Dragon AI)
- Composer placeholder + `:focus-visible` ring (`2px` solid `--color-ring`, offset `2px`)
- Settings / About product copy (strings already in `desktop_branding.json`)
- Shared CSS variables so a later branded Electron build can reuse them

Do **not** paint `html`/`body` backgrounds (upstream owns theme). Do **not** change `127.0.0.1:8650`, `dragon-local`, `hermes-airmaze-gw`, or `hermes-airmaze-desktop`.

## Anti-patterns (keep from MASTER)

- Heavy chrome, slow response feedback
- Emojis as icons
- Invisible focus
- Ignoring `prefers-reduced-motion`
- AI purple / pink gradients
- New CSS/JS frameworks
