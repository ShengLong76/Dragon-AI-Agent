# Plan — apply the Dragon AI Agent design system

Small plan after `docs/airmaze/DESIGN.md`. No new framework. Keep existing overlay + tests.

## In scope

1. Install open-source UI UX Pro Max for Cursor in-repo (`.cursor/skills/ui-ux-pro-max` only; drop the paid brand/logo extras the CLI also unpacked).
2. Persist the generator output to `design-system/dragon-ai-agent/MASTER.md` and write `pages/desktop-client.md`.
3. Extend `branding/fonts/syne/dragon-ui.css` with the applied tokens and overlay chrome (wordmark, empty-state subtitle, composer focus/placeholder, reduced motion, front-facing dragon mark). Keep Syne `@font-face` and the Collapse alias.
4. Point the wizard color block at those tokens (same RGB, documented). Do not retune Bot Screen or `desktop_branding.json` product strings except a version/token note.
5. Document in `BRANDING.md`, `CHANGELOG.md`, `THIRD_PARTY_NOTICES.md`, `README.md`.
6. Extend `Test-DesktopBranding.py` / overlay self-test so validation is not cut: skill present, design-system note present, Syne 700, no Tesla/Inter wordmark, tokens match, protected gateway strings survive.

## Out of scope

- Rebuilding Hermes.exe or rewriting `app.asar`
- Changing `127.0.0.1:8650`, `dragon-local`, `hermes-airmaze-gw`, `hermes-airmaze-desktop`
- Vendoring Inter, Universal Sans, Gotham, or Tesla faces
- Adding Tailwind, React, GSAP, or any other UI kit
- Touching a Windows machine
