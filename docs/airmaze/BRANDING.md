# Dragon AI Agent branding

Customer-facing product name is **Dragon AI Agent** (Dragon's Den / dragonsden.work).  
Logo assets in this repo: `branding/dragon-ai-agent-logo.png`, `dragon-ai-agent-logo-256.png`, `dragon-ai-agent-logo.ico`.

Internal protocol, image, and path names stay Hermes/AirMaze where changing them would break Docker, volumes, or the Electron client on disk.

## What PowerShell packaging can brand (this repo)

| Surface | What James sees |
|---------|-----------------|
| Desktop / Start Menu shortcuts | **Dragon AI Agent** → `wscript.exe` + `Start-DragonAI.vbs` (no console). Also Profiles, Setup, optional Dashboard |
| Shortcut descriptions | “start the gateway and open the app” |
| Installer exe | `DragonAIAgentSetup.exe` — ProductName / FileDescription **Dragon AI Agent** (`installer/winres/winres.json`) |
| Onboarding wizard | Window title **Dragon AI Agent Setup**; welcome copy; dragon logo in the header |
| Launch status / error dialogs | **Dragon AI Agent** |
| Install-root pointer | `Dragon AI Agent Client.lnk` + `desktop-client.json` (target is still `Hermes.exe`) |
| Electron **window title** | Packaging wrap: all visible Hermes windows → **Dragon AI Agent** (`SetTitleForPids`) |
| Empty state heading | Overlay: **DRAGON AI AGENT** (was `HERMES AGENT` in `apps/desktop/src/components/chat/intro.tsx`) |
| Composer placeholder | Overlay: **Give Dragon AI a task** (was `Give Hermes a task`) |
| Settings / About / setup product copy | Overlay: **Dragon AI Agent** wherever the renderer said **Hermes Agent** (and About / appName chrome) |
| In-window UI font | Overlay: **Outfit** (SIL OFL 1.1), bundled under `branding/fonts/outfit` and injected as `dragon-ai-branding/dragon-ui.css` into the unpacked renderer |
| Dashboard login | Username `dragon` / password `dragon-local` (loopback only). Page chrome/title inside the image is still upstream until a branded build or image exists. |
| Profile catalog / Real Estate labels | Dragon AI Agent (not AirMaze/Hermes as the product) |

## In-app overlay (no Electron rebuild)

The shipped client is still upstream `Hermes.exe` (`…\win-unpacked\Hermes.exe`). This package does **not** contain `apps/desktop` source and does not rebuild it.

Upstream `electron-builder` packs most of the app into `resources/app.asar` (integrity-protected — do not rewrite that archive) and **unpacks `dist/**`** to `resources/app.asar.unpacked/dist`. The empty-state wordmark, composer placeholders, and settings strings live in that unpacked renderer.

`Apply-DesktopBranding.ps1` / `desktop_branding.py` run from `Start-HermesDesktopClient` (every launch, idempotent) and rewrite those files in place. Table: `scripts/airmaze/desktop_branding.json`. Offline check: `python3 scripts/airmaze/Test-DesktopBranding.py`.

### UI font (Outfit)

Tesla’s car/site type is **Universal Sans** (proprietary). This overlay does **not** vendor or claim that font.

The in-window face is **[Outfit](https://github.com/Outfitio/Outfit-Fonts)** (SIL OFL 1.1): a geometric grotesque in the Gotham / Universal Sans neighborhood (even stroke, high x-height, simple terminals, drawn for digital UI). Latin `woff2` files ship in the package so UltraDragon does not need the font installed. The overlay copies them into `resources/app.asar.unpacked/dist/dragon-ai-branding/` and links `dragon-ui.css` from the renderer `index.html`, covering the empty-state wordmark, composer, and the rest of the product chrome the string overlay already touches. Icon fonts (codicon, etc.) keep their own `font-family`.

This is the smallest durable path that actually changes what the user sees without forking or rebuilding Electron. Re-applying after a Hermes.exe update puts the Dragon copy back.

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
| Default bot **id** `hermes` on disk | Do not rename; only display chrome is overlaid when the string is product copy |
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
