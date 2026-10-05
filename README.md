<p align="center">
  <img src="branding/dragon-logo.png" alt="Dragon AI" width="220">
</p>

# Dragon AI

Dragon AI is a desktop AI workspace built around **bot teams**. You chat with a Chief of Staff bot that routes work to specialist bots. Each bot has its own role, skills library, scheduled routines, and an optional VM desktop ("computer") you can watch it work on.

It is a fork of the open-source [Hermes Agent](https://github.com/NousResearch/hermes-agent) framework (MIT), rebranded and extended. Everything a user sees, including the window, tray, installer, CLI messages, and process name, says Dragon AI.

## What's in the app

- **Grok-first onboarding.** Providers are expanded on the first screen, with xAI Grok OAuth (SuperGrok / Premium+) recommended. A confirmation screen shows the connected provider and default model (`grok-4.7`), with **Change** and **Begin** buttons. Begin lands on the Bots tab with the Chief of Staff's screen open.
- **Bots tab.** Pinned bots appear as avatar tiles with a name and role badge, sorted to the top. Double-click any bot to open the right-hand **bot panel**, which has three tabs:
  - **Computer:** the bot's VM desktop.
  - **Library:** the bot's skills.
  - **Details:** the bot's profile and its Routines toggles.
- **Teams Marketplace.** This is the row under the Dragon logo in the sidebar. Install a ready-made team (Real Estate Lead Gen, Marketing, Trading Desk, Engineering, Customer Support, Research) in one click. Each seat becomes a bot with its own persona, role, color, and section in the roster.
- **Duplex voice.** In Settings → Voice → Voice conversation mode, choose **Chained** (speech-to-text, then LLM, then text-to-speech), **GPT-Live**, or **Grok Voice**. Grok Voice uses xAI's realtime voice API and delegates real work back to the agent through an `ask_dragon` tool. A floating waveform widget sits above the composer while a conversation is live.
- **Scheduled jobs.** Opening Scheduled Jobs keeps the right sidebar visible.
- **Telemetry.** Dragon AI never prompts you to share usage metrics. The opt-in lives in Settings → Safety and is off by default.

## Requirements

- Node.js `^22.22`, `^24.11`, or `>=26`
- Linux, macOS, or Windows (Windows installers are built on a Windows host)
- An AI provider. SuperGrok / X Premium+ OAuth is recommended. `XAI_API_KEY`, or any provider Hermes supports, also works.

## Run it locally

```bash
# 1. Backend: pm-managed Python environment (uv + pinned interpreter)
export HERMES_HOME="$HOME/.dragon-ai-claude"
./setup-hermes.sh
source ./activate

# 2. Desktop app
npm install
cd apps/desktop
npm run dev          # Vite renderer on http://127.0.0.1:5174, then Electron
```

The desktop app starts its own backend process and keeps all state in `~/.dragon-ai-claude`. On first launch you'll go through onboarding. Pick **xAI Grok OAuth**, sign in, confirm the model, and press **Begin**.

The CLI is also available as `dragon` (for example `dragon model` or `dragon auth add xai-oauth`).

## Build installers

From `apps/desktop`:

| Target  | Command              | Output                                             |
| ------- | -------------------- | -------------------------------------------------- |
| Windows | `npm run dist:win`   | One `DragonAIClaude-Setup-<version>-<arch>.exe` (NSIS) |
| macOS   | `npm run dist:mac`   | `.dmg` and `.zip`                                  |
| Linux   | `npm run dist:linux` | AppImage, `.deb`, `.rpm`                           |

The Windows installer is a single self-contained Setup `.exe`. It lets you choose the install directory, creates Start-menu and desktop shortcuts, and launches the app when it finishes. `npm run dist:win:msix` still builds an MSIX package if you need one.

## Tests and checks

```bash
# Python
HERMES_HOME=$HOME/.dragon-ai-claude scripts/run_tests.sh tests/tools tests/agent

# Desktop
cd apps/desktop
npm run typecheck
npm run lint
npx vitest run
```

## Staying in sync with upstream

This fork is based on `NousResearch/hermes-agent@af90026`. Internal module names (`hermes_cli`, `tui_gateway`, …) are kept so upstream changes merge cleanly. Only user-visible strings are rebranded, using a script that rewrites string literals and JSX text and never touches identifiers or storage keys:

```bash
python3 scripts/dragon/rebrand_strings.py           # rewrite in place
python3 scripts/dragon/rebrand_strings.py --check   # fail if any visible upstream naming remains
```

Run it after every upstream merge. Dragon-specific code lives in `apps/desktop/src/dragon/` (brand, theme, Teams Marketplace) and `apps/desktop/src/plugins/hermes-bots/` (bot panel, pinned tiles, roster).

## Known limits

- The hands-free wake word is a bundled on-device model trained on the phrase "hey hermes". Rebranding it needs a newly trained model, so the phrase is unchanged for now.
- On Windows, the backend's console shim is still named `hermes.exe`. The updater and process-cleanup code match on that name.

## License

MIT. See [LICENSE](LICENSE). Includes Hermes Agent © Nous Research, used under the MIT license.
