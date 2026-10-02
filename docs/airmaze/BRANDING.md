# Dragon AI Agent branding

Customer-facing product name is **Dragon AI Agent** (Dragon's Den / dragonsden.work).  
Logo assets in this repo: `branding/dragon-ai-agent-logo.png` (James’s navy coiled mark, cropped), `dragon-ai-agent-logo.svg` (facet companion), `dragon-ai-agent-logo-256.png`, `dragon-ai-agent-logo.ico`. Front-facing low-poly dragon — coiled neck, horns the same navy as the body, red eyes. No gold, no copper ring, not a side profile. Rebuild with `python3 branding/render_logo.py`.

Internal protocol, image, and path names stay Hermes/AirMaze where changing them would break Docker, volumes, or the Electron client on disk.

## What PowerShell packaging can brand (this repo)

| Surface | What James sees |
|---------|-----------------|
| Desktop / Start Menu shortcuts | **Dragon AI Agent** only → `wscript.exe` + `Start-DragonAI.vbs` (no console). No Bot Groups / Dashboard / Profiles / Setup `.lnk` (leftovers deleted on install and launch) |
| Shortcut descriptions | “start the gateway and open the app” |
| Installer exe | `DragonAIAgentSetup.exe` — ProductName / FileDescription **Dragon AI Agent** (`installer/winres/winres.json`) |
| Onboarding wizard | Window title **Dragon AI Agent Setup**; welcome copy; dragon + title on a **blue** `#2563EB` header band (buttons stay crimson) |
| Launch status / error dialogs | **Dragon AI Agent** on the same blue header band |
| Install-root pointer | `Dragon AI Agent Client.lnk` + `desktop-client.json` (target is still `Hermes.exe`) |
| Electron **window title** | Packaging wrap: all visible Hermes windows → **Dragon AI Agent** (`SetTitleForPids`) |
| Empty state heading | Overlay: **DRAGON AI AGENT** (was `HERMES AGENT` in `apps/desktop/src/components/chat/intro.tsx`), Syne 700, **in front of** a larger unboxed navy dragon |
| Empty state mark | Overlay: James’s navy PNG with the black plate punched; no boxed background |
| Sidebar header | Overlay: navy dragon + **Dragon AI** + **blue Teams Marketplace** above Sessions / Bots (order: lockup → Teams Marketplace → Sessions/Bots). **56px** mark (1.75×) sits to the right of hide-sidebar. Full label, reserved gap under the logo (no overlay). Column hosts first; else in-flow `[data-dragon-ai-sidebar-chrome]`; else body `[data-dragon-ai-sidebar-fixed]` in a first-child clearance spacer (do not cover those tabs). Sidebar and middle session names share 16px (`docs/airmaze/SIDEBAR_HOST.md`, `docs/airmaze/PACKAGING_CHROME.md`) |
| Bots sidebar | **Exclude** the built-in default **Hermes** agent (purge `profiles\\hermes` / `default`; CSS hide of `data-roster-key` `::default` is the backstop). **Personal Assistant** stays |
| Bot groups in BOTS | Deploy/import stamps `sectionId` / `sectionName` so the pack sits in a named section (not UNASSIGNED) |
| Running app / taskbar icon | Contain-max sidebar-mark ICO + PNG (navy low-poly, no copper rim) copied over Hermes `resources/icon.ico`, `icon.png`, and unpacked `dist/apple-touch-icon.png`; stamp `Hermes.exe` when `rcedit` is on PATH. Shortcuts use the same ICO. Private `DragonAIAgent` tree only. Design: `docs/airmaze/TRAY_ICON.md`, `docs/airmaze/DURABLE_BRANDING.md` |
| Composer placeholder | Overlay: **Give Dragon AI a task** (was `Give Hermes a task`) |
| Voice chat provider | Settings → Voice → Voice conversation mode: **Chained**, **Gpt-live**, **Grok Voice**. Same `voice.voice_chat_mode` key as gpt-live. Composer GPT/Grok pills are removed. Right-side **waveform** opens the Grok-Bot capsule (avatar \| bars \| **gear** \| chat \| mic \| red X). Gear is Voice settings (official xAI voice, speed, language, interrupt). GPT (Hermes `gpt-live`) stays. Helper `127.0.0.1:8654`. See `docs/airmaze/VOICE.md` |
| Settings / About / setup product copy | Overlay: **Dragon AI Agent** wherever the renderer said **Hermes Agent** (and About / appName chrome) |
| In-window UI font | Overlay: **Syne** (SIL OFL 1.1, weight **700** on the wordmark) replacing upstream **Collapse** / Collapse-Bold, then composer and settings chrome |
| Dashboard login | Username `dragon` / password `dragon-local` (loopback only). Page chrome/title inside the image is still upstream until a branded build or image exists. |
| Bot group catalog / Real Estate labels | Dragon AI Agent (not AirMaze/Hermes as the product) |

## In-app overlay (no Electron rebuild)

The shipped client is still upstream `Hermes.exe`, but Dragon AI runs a **private copy** at `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\Hermes.exe` with `HERMES_DESKTOP_USER_DATA_DIR=%LOCALAPPDATA%\DragonAIAgent\electron-userdata`. This package does **not** contain `apps/desktop` source and does not rebuild it. The standalone Hermes tree is a read-only source. Branding is **refused** outside `DragonAIAgent`. See `docs/airmaze/PRIVATE_DESKTOP.md`.

Upstream `electron-builder` packs most of the app into `resources/app.asar` (integrity-protected — do not rewrite that archive) and **unpacks `dist/**`** to `resources/app.asar.unpacked/dist`. The empty-state wordmark, composer placeholders, and settings strings live in that unpacked renderer.

`Apply-DesktopBranding.ps1` run from `Start-HermesDesktopClient` (every launch, idempotent) rewrites those files **only on the private Dragon copy**. Table: `scripts/airmaze/desktop_branding.json`. The same pass injects the sidebar header lockup, copies the Dragon SVG/PNG into `dist/dragon-ai-branding/` (hard-fail if missing), and copies the Dragon ICO/PNG onto Hermes `resources/icon.ico`, `icon.png`, and unpacked `apple-touch-icon.png`. **Python is optional.** PowerShell always copies the prebuilt `branding/fonts/syne` pack (`dragon-ui.css`, inject `.js`, fonts, logos) into every discovered `app.asar.unpacked\dist\dragon-ai-branding\` under `%LOCALAPPDATA%\DragonAIAgent\` and upserts `index.html`. It refuses a path outside `DragonAIAgent`, does not skip when `index.html` is already branded, and it throws if the CSS or required logo files do not land. Offline check: `python3 scripts/airmaze/Test-DesktopBranding.py` / `Test-TrayIcon.py` / `Test-PrivateDesktop.py`. Launch also runs `exclude_hermes_bot.py` so leftover Hermes profile folders are dropped, not only hidden. Durable contract: `docs/airmaze/DURABLE_BRANDING.md`.

### How UltraDragon apply must be run so unpacked UI updates

Close `Hermes.exe` first so `index.html` / `dragon-ui.css` are not locked. Then either:

1. **Relaunch Dragon AI Agent** (Start Menu / `Start-DragonAI.vbs`). Launch calls `Apply-DragonAIDesktopUiBranding` before the window opens. `python3` / `python` do **not** need to be on PATH.
2. **Manual apply** against the live exe (PowerShell):

```powershell
$exe = (Get-Content "$env:LOCALAPPDATA\DragonAIAgent\desktop-client.json" -Raw | ConvertFrom-Json).exe
powershell -NoProfile -File "$env:LOCALAPPDATA\DragonAIAgent\scripts\airmaze\Apply-DesktopBranding.ps1" -ExePath $exe
```

Confirm the live sheet is the tip pack (must contain `dragon-ai-lockup-wrap:1`, `dragon-ai-marketplace-label:1`, `dragon-ai-marketplace-blue:1`, `dragon-ai-logo-clearance:1`, `dragon-ai-logo-175:1`, `dragon-ai-composer-chrome:1`, `dragon-ai-chat-bubbles:1`; must not contain `border:1px solid rgba(196,30,58`):

`%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\resources\app.asar.unpacked\dist\dragon-ai-branding\dragon-ui.css`

Do **not** look under `%LOCALAPPDATA%\hermes\…` — that standalone tree is not branded. Updating only the git checkout / install-root `branding/fonts/syne/dragon-ui.css` does nothing until this apply copies it.

### UI font (Syne) — empty-state wordmark first

The red-boxed empty-state heading is not body text. Upstream sets `.wordmark { font-family: 'Collapse' }` and loads **Collapse-Bold** (`@nous-research/ui`): a high-contrast display face (thick/thin strokes). That is why “DRAGON AI AGENT” still looks serif-like after the string overlay.

**Universal Sans**, Gotham, and other Tesla UI faces are proprietary. This overlay does **not** vendor or claim those fonts.

The replacement face is **[Syne](https://gitlab.com/bonjour-monde/fonderie/syne-typeface)** (SIL OFL 1.1): James picked this OFL variable sans. The wordmark uses **weight 700**; composer and the other product chrome the overlay already touches use the same family. The overlay:

1. Rewrites unpacked CSS `font-family: 'Collapse'` on `.wordmark` to `Syne`
2. Bundles Latin `woff2` (variable + 400/600/700) under `branding/fonts/syne/` and copies them into `resources/app.asar.unpacked/dist/dragon-ai-branding/`
3. Injects `dragon-ui.css` (also registers the files as `font-family: Collapse` so leftover rules cannot reload Collapse-Bold)
4. Appends those rules to the renderer’s own CSS, rewriting `url()` so `assets/*.css` still finds the pack

Icon fonts keep their own `font-family`. UltraDragon does not need the font installed.

This is the smallest durable path that actually changes what the user sees without forking or rebuilding Electron. Re-applying after a Hermes.exe update puts the Dragon copy back.

### Design system (UI UX Pro Max, open-source)

The Cursor skill is installed in-repo at `.cursor/skills/ui-ux-pro-max` (`npx ui-ux-pro-max-cli init --ai cursor`; paid brand/logo extras are not kept). Generator output: `design-system/dragon-ai-agent/MASTER.md`. Applied chrome: `pages/desktop-client.md` and `docs/airmaze/DESIGN.md`.

Style is **AI-Native UI** (minimal chrome, single accent). Catalog Inter and AI purple are not shipped. Overlay tokens match the existing wizard: dark `#1C1C20` / `#282830`, crimson `#C41E3A`, Syne 700 on the wordmark, visible `:focus-visible`, `prefers-reduced-motion`. Sidebar / chat / Teams type is Grok Bot–sized (**16px** body, **14px** chrome, muted `#C4C4CE`) by remapping Hermes `--conversation-text-base-size` and `--ui-text-*` — no `Hermes.exe` rebuild. The transcript pane is **black** with blue-shade user (`#2563EB`) and assistant (`#17345A`) bubbles (`docs/airmaze/CHAT_BUBBLES.md`). No new UI framework.

## What still requires a rebuilt Electron binary

Until someone builds a branded client (`productName`, `appId`, icons, tray, About):

| Surface | Still says Hermes (or similar) |
|---------|--------------------------------|
| Process / exe filename | `Hermes.exe` |
| Taskbar jump list / AppUserModelID | Upstream appId (`com.nousresearch.hermes`) |
| System tray tooltip | Upstream string (not in unpacked `dist/**`) |
| `app.asar` extras (icons, some package metadata) | Integrity-protected; overlay will not touch them |
| Hermes Cloud / catalog / protocol `hermes://` | Upstream service and wire names — leave them |
| License / NOTICE files next to the exe | Attribution stays **Hermes Agent** / Nous Research |
| Default bot **id** `default` / `hermes` on disk | Do not rename the id; the sidebar row is hidden so James only sees Personal Assistant |
| Window title after the client resets it | May revert to Hermes until wrap re-applies or a branded build ships |

To ship a true Dragon AI Agent binary, rebuild the desktop app with e.g. `productName: "Dragon AI Agent"`, a new `appId`, and the `branding/dragon-ai-agent-logo.*` icons — then point `Find-HermesDesktop.ps1` at that exe (or keep the current path if the file is still named `Hermes.exe`).

## Do not rename (breaks the stack)

- Docker image `nousresearch/hermes-agent:latest-desktop`
- Container name `hermes-airmaze-gw`, compose project `airmaze-embedded`
- Data dir `%USERPROFILE%\.hermes-airmaze-embedded`
- Env prefix `HERMES_*`, `API_SERVER_*`
- Profile copy target `%LOCALAPPDATA%\hermes\profiles\<bot-id>\`
- On-disk discovery of standalone `Hermes.exe` under `%LOCALAPPDATA%\hermes\…` (source for the private copy only)
- Desktop Remote `http://127.0.0.1:8650` + `X-Hermes-Session-Token` / `dragon-local` (Bot Screen)
