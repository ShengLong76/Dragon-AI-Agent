# Dragon AI Agent branding

Customer-facing product name is **Dragon AI Agent** (Dragon's Den / dragonsden.work).  
Logo assets in this repo: `branding/dragon-ai-agent-logo.png` (James’s navy coiled mark, cropped), `dragon-ai-agent-logo.svg` (facet companion), `dragon-ai-agent-logo-256.png`, `dragon-ai-agent-logo.ico`. Front-facing low-poly dragon — coiled neck, horns the same navy as the body, red eyes. No gold, no copper ring, not a side profile. Rebuild with `python3 branding/render_logo.py`.

Internal protocol, image, and path names stay Hermes/AirMaze where changing them would break Docker, volumes, or the Electron client on disk.

## What PowerShell packaging can brand (this repo)

| Surface | What James sees |
|---------|-----------------|
| Desktop / Start Menu shortcuts | **Dragon AI Agent** → `wscript.exe` + `Start-DragonAI.vbs` (no console). Also Bot Groups, Setup, optional Dashboard |
| Shortcut descriptions | “start the gateway and open the app” |
| Installer exe | `DragonAIAgentSetup.exe` — ProductName / FileDescription **Dragon AI Agent** (`installer/winres/winres.json`) |
| Onboarding wizard | Window title **Dragon AI Agent Setup**; welcome copy; dragon logo in the header |
| Launch status / error dialogs | **Dragon AI Agent** |
| Install-root pointer | `Dragon AI Agent Client.lnk` + `desktop-client.json` (target is still `Hermes.exe`) |
| Electron **window title** | Packaging wrap: all visible Hermes windows → **Dragon AI Agent** (`SetTitleForPids`) |
| Empty state heading | Overlay: **DRAGON AI AGENT** (was `HERMES AGENT` in `apps/desktop/src/components/chat/intro.tsx`), Syne 700, **in front of** a larger unboxed navy dragon |
| Empty state mark | Overlay: James’s navy PNG with the black plate punched; no boxed background |
| Sidebar header | Overlay: navy dragon + **Dragon AI** above SESSIONS / BOTS (accessible name **Dragon AI Agent**) |
| Bots sidebar | **Exclude** the built-in default **Hermes** agent (purge `profiles\\hermes` / `default`; CSS hide of `data-roster-key` `::default` is the backstop). **Personal Assistant** stays |
| Bot groups in BOTS | Deploy/import stamps `sectionId` / `sectionName` so the pack sits in a named section (not UNASSIGNED) |
| Running app / taskbar icon | Copy the Dragon ICO over `resources/icon.ico` and stamp `Hermes.exe` when a PE stamper is available |
| Composer placeholder | Overlay: **Give Dragon AI a task** (was `Give Hermes a task`) |
| Voice chat provider | Overlay: **GPT** and **Grok** as two selectable options. GPT (Hermes `gpt-live`) stays. **Talk with Grok** hosts official xAI full duplex (`grok-voice-latest`). Helper `127.0.0.1:8654`. See `docs/airmaze/VOICE.md` |
| Settings / About / setup product copy | Overlay: **Dragon AI Agent** wherever the renderer said **Hermes Agent** (and About / appName chrome) |
| In-window UI font | Overlay: **Syne** (SIL OFL 1.1, weight **700** on the wordmark) replacing upstream **Collapse** / Collapse-Bold, then composer and settings chrome |
| Dashboard login | Username `dragon` / password `dragon-local` (loopback only). Page chrome/title inside the image is still upstream until a branded build or image exists. |
| Bot group catalog / Real Estate labels | Dragon AI Agent (not AirMaze/Hermes as the product) |

## In-app overlay (no Electron rebuild)

The shipped client is still upstream `Hermes.exe` (`…\win-unpacked\Hermes.exe`). This package does **not** contain `apps/desktop` source and does not rebuild it.

Upstream `electron-builder` packs most of the app into `resources/app.asar` (integrity-protected — do not rewrite that archive) and **unpacks `dist/**`** to `resources/app.asar.unpacked/dist`. The empty-state wordmark, composer placeholders, and settings strings live in that unpacked renderer.

`Apply-DesktopBranding.ps1` / `desktop_branding.py` run from `Start-HermesDesktopClient` (every launch, idempotent) and rewrite those files in place. Table: `scripts/airmaze/desktop_branding.json`. The same pass injects the sidebar header lockup and copies the Dragon ICO to `resources/icon.ico`. Offline check: `python3 scripts/airmaze/Test-DesktopBranding.py`. Launch also runs `exclude_hermes_bot.py` so leftover Hermes profile folders are dropped, not only hidden.

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

Style is **AI-Native UI** (minimal chrome, single accent). Catalog Inter and AI purple are not shipped. Overlay tokens match the existing wizard: dark `#1C1C20` / `#282830`, crimson `#C41E3A`, Syne 700 on the wordmark, visible `:focus-visible`, `prefers-reduced-motion`. Sidebar / chat / Teams type is Grok Bot–sized (**16px** body, **14px** chrome, muted `#C4C4CE`) by remapping Hermes `--conversation-text-base-size` and `--ui-text-*` — no `Hermes.exe` rebuild. No new UI framework.

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
- On-disk discovery of `Hermes.exe` under `%LOCALAPPDATA%\hermes\…`
- Desktop Remote `http://127.0.0.1:8650` + `X-Hermes-Session-Token` / `dragon-local` (Bot Screen)
