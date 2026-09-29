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
| Electron **window title** | Best-effort wrap: after start, `SetWindowText` → **Dragon AI Agent** |
| Dashboard login | Username `dragon` / password `dragon-local` (loopback only) |
| Profile catalog / Real Estate labels | Dragon AI Agent (not AirMaze/Hermes as the product) |

## What still requires a rebuilt Electron binary

The shipped client is upstream `Hermes.exe` (`…\win-unpacked\Hermes.exe`). This package does **not** contain `apps/desktop` source and does not rebuild it.

Until someone builds a branded client (`productName`, `appId`, icons, tray, About):

| Surface | Still says Hermes (or similar) |
|---------|--------------------------------|
| Process / exe filename | `Hermes.exe` |
| Taskbar jump list / AppUserModelID | Upstream appId |
| System tray tooltip | Upstream string |
| In-app About / Settings chrome | Upstream “Hermes” |
| Window title after the client resets it | May revert to Hermes until wrap re-applies or a branded build ships |

To ship a true Dragon AI Agent binary, rebuild the desktop app with e.g. `productName: "Dragon AI Agent"`, a new `appId`, and the `branding/dragon-ai-agent-logo.*` icons — then point `Find-HermesDesktop.ps1` at that exe (or keep the current path if the file is still named `Hermes.exe`).

## Do not rename (breaks the stack)

- Docker image `nousresearch/hermes-agent:latest-desktop`
- Container name `hermes-airmaze-gw`, compose project `airmaze-embedded`
- Data dir `%USERPROFILE%\.hermes-airmaze-embedded`
- Env prefix `HERMES_*`, `API_SERVER_*`
- Profile copy target `%LOCALAPPDATA%\hermes\profiles\<bot-id>\`
- On-disk discovery of `Hermes.exe` under `%LOCALAPPDATA%\hermes\…`
