# Plan — blue header lockup band

Small plan after `docs/airmaze/HEADER_LOCKUP_BLUE.md`. Tests first. Draft PR only. Do not merge.

## In scope

1. `Onboard-Wizard.ps1` — add `BrandBlue` `#2563EB` / `37, 99, 235`. Header panel uses it. `New-BrandButton -Primary` stays `BrandRed`.
2. `start-embedded.ps1` — launch-status header `FromArgb(37, 99, 235)`.
3. `Select-BotGroup.ps1` — same header token. Launch button stays crimson.
4. Subtitle on those bands: `#F0F0F5` / White (drop pink-on-red `255, 220, 220`).
5. Record `headerBand: #2563EB` in `desktop_branding.json` + `pages/desktop-client.md`. One line in `DESIGN.md` / `BRANDING.md` / `CHANGELOG.md`.
6. Tests: header is blue, not `BrandRed`; primary buttons still `196, 30, 58`.

## Tests first

- Wizard / launch / Teams WinForms: `$header.BackColor` is `BrandBlue` or `37, 99, 235`. Fail if `$header.BackColor = $script:BrandRed` or header `196, 30, 58`.
- Primary Continue / Launch still `BrandRed` / `196, 30, 58`.
- Overlay CSS still has no crimson lockup border; sidebar brand stays `background: transparent`.
- `tokens.headerBand` is `#2563EB`; `tokens.primary` stays `#C41E3A`.

## Out of scope

- Electron sidebar lockup fill
- Live UltraDragon
- Merging this PR
