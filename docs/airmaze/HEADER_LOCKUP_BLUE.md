# Dragon AI Agent — blue header lockup band

Short design after James: the band behind the dragon + **Dragon AI Agent** title is bright red; it should be blue. Packaging / WinForms chrome only. No `Hermes.exe` rebuild. Do not merge.

## Surfaces

The red lockup is the **WinForms title band** (logo + product name), not the in-app sidebar inject.

| Surface | File | Change |
|---------|------|--------|
| Onboard wizard | `scripts/airmaze/Onboard-Wizard.ps1` | `$header.BackColor` → Marketplace blue |
| Launch status | `scripts/airmaze/start-embedded.ps1` `New-LaunchStatusForm` | same RGB (form kept; **not shown** on normal launch) |
| Teams Marketplace (WinForms) | `scripts/airmaze/Select-BotGroup.ps1` | same token (product name in the band) |

**Leave alone**

- Primary / Continue / Launch **buttons** stay crimson `#C41E3A`
- Composer focus / selected GPT|Grok stay crimson
- Dragon eyes stay `#C41E3A`
- Electron sidebar lockup (`[data-dragon-ai-sidebar-brand]`) is already transparent on `#1C1C20` (no red band). Do not paint a blue plate behind the 32px SVG — that would fight the dark rail and the blue Marketplace button under it.

## Token

Reuse the existing Teams Marketplace blue — do not invent a third blue.

| Role | Hex | RGB | Already used |
|------|-----|-----|--------------|
| Header band | `#2563EB` | `37, 99, 235` | `--dragon-marketplace-blue`, `[data-dragon-ai-teams-open]` |
| Title on band | `#FFFFFF` | White | on-blue (large / bold) |
| Subtitle on band | `#F0F0F5` | `240, 240, 245` | `--color-foreground` |

White on `#2563EB` is ~5.2:1 (clears 4.5:1 and the 3:1 large-text bar). Pink-on-red subtitle `255, 220, 220` and wizard muted `#A0A0AA` both fail on blue — subtitle uses `#F0F0F5` (~4.5:1).

UI UX Pro Max: Color Contrast (High). No verified “sidebar brand lockup” row.

## Out of scope

- Restyling Bot Screen / ports / tokens
- Painting the Electron sidebar lockup blue
- Changing `--color-primary`
- Live UltraDragon click-through
- Merging
