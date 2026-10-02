# Durable Dragon logo + tray on the private desktop

Short design after James’s UltraDragon notes: the sidebar lockup shows a **missing logo**, and the running-app / tray / taskbar icon is still the **Hermes** mark. Live tip is applied separately. This note is the durable packaging contract so a **fresh install** or **rebrand apply** always lands Dragon assets on the private tree and **never** mutates standalone Hermes.

Packaging overlay only. No `Hermes.exe` rebuild. No `app.asar` rewrite. Bot Screen stays `127.0.0.1:8650` / `dragon-local`. Plan: `docs/airmaze/DURABLE_BRANDING_PLAN.md`.

## What James marked

1. **Sidebar logo is missing** (broken image) in the Dragon AI Agent chrome.
2. **Tray / taskbar is Hermes** (purple rounded square), not the navy Dragon mark.

## How those surfaces are applied today

| Surface | Engine | What must land |
|---------|--------|----------------|
| Sidebar lockup `<img>` | `sidebar-header.js` → `./dragon-ai-branding/dragon-ai-agent-logo.svg` | File **must exist** next to the injected CSS/JS in unpacked `dist/dragon-ai-branding/` |
| Empty-state mark | `dragon-ui.css` → `url("./dragon-ai-agent-logo.png")` | Same pack folder |
| Windows / Electron window + tray | Hermes `appIconCandidates` (upstream `apps/desktop/electron/app-icon.ts`) | On Windows: `{resources}/icon.ico`, then unpacked `dist/apple-touch-icon.png`, `public/apple-touch-icon.png`, `dist/apple-touch-icon.png`. Tray `nativeImage.createFromPath` uses that ladder / `icon.png`. |
| PE resource on `Hermes.exe` | `rcedit --set-icon` | Best-effort only (no stamper on PATH must not block apply of ICO/PNG files) |
| Shortcuts | `.lnk` `IconLocation` | Already `branding/dragon-ai-agent-logo.ico` |

Apply is `Apply-DesktopBranding.ps1` / `desktop_branding.py` against `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\Hermes.exe`. The standalone `%LOCALAPPDATA%\hermes\…` tree is source-only.

## Root cause (durable, not a one-off tip)

1. **Logo copy is best-effort.** PowerShell / Python skip `dragon-ai-agent-logo.svg` / `.png` when the install-root `branding\` files are missing, then still report success. The inject keeps the `src`, so the rail shows a missing image.
2. **Tray copy is ICO-only and silent.** Apply overwrites `icon.ico` when a source exists, but Hermes also reads **`apple-touch-icon.png`** and **`icon.png`** from the private `win-unpacked` resources. Those stay the upstream Hermes mark. If the ICO source is missing, apply returns `copied: false` and continues.
3. **`stamp_app_icon` does not refuse a non-Dragon path.** `apply_to_exe` refuses, but the ICO helper can write into a standalone Hermes tree if called directly. That violates the private-desktop contract.

Do not invent a new mark. Same navy sidebar PNG / contain-max ICO as `docs/airmaze/TRAY_ICON.md`.

## Do (every install + every apply, idempotent)

1. **Require** `branding/dragon-ai-agent-logo.svg` and `.png` (and the ICO) in the install root. Installer and apply **hard-fail** if a required logo is missing — no silent skip.
2. Copy SVG + PNG into every unpacked `dist/dragon-ai-branding/` and verify the files are present. The inject/CSS references stay the existing relative paths.
3. Copy the Dragon **ICO** over Hermes `icon.ico` paths (resources, beside the exe, `app` / `app.asar.unpacked` when those folders exist, plus any existing `icon.ico` under `resources\`).
4. Copy the Dragon **PNG** over Electron PNG candidates on the **private** tree:
   - `{exeDir}\resources\icon.png` and `{exeDir}\icon.png`
   - `{unpacked}\dist\apple-touch-icon.png` (create when `dist` exists)
   - `{unpacked}\public\apple-touch-icon.png` when `public` exists
   - any existing `icon.png` / `apple-touch-icon.png` under `resources\` (skip `node_modules`)
5. **Refuse** branding / icon stamp / overlay outside a path that contains `DragonAIAgent` (same message: `Refuse branding outside DragonAIAgent`). Standalone Hermes is not mutated.
6. PE stamp stays best-effort. File ICO/PNG apply is required.

Python remains optional: PowerShell must do the same copies and the same hard-fail.

## Out of scope

- Rebuilding `Hermes.exe` / rewriting `app.asar`
- Changing Bot Screen ports, tokens, or image names
- A new logo or a fixed tray pixel size
- Live UltraDragon tip (verify steps only; Cos applies separately)
- Merging (James merges)
