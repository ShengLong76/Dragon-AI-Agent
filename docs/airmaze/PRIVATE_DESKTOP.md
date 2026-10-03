# Dragon AI Agent is its own Windows app

Short contract after James rejected the Hermes.exe hunt. Packaging only. Hermes stays a separate product.

## Paths

| Program | Desktop tree | User data |
|---------|--------------|-----------|
| **Dragon AI Agent** | `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\DragonAIAgent.exe` | `HERMES_DESKTOP_USER_DATA_DIR=%LOCALAPPDATA%\DragonAIAgent\electron-userdata` |
| **Standalone Hermes** | untouched | `%APPDATA%\Hermes` |

Install/start copy `DragonAIAgent.exe` from the **Dragon package** (`payload/desktop/win-unpacked` or `vendor/desktop`). They do not search for, copy, require, or mention a Hermes install. They never write back into a Hermes tree. The window is the UltraDragon shell (dark rail, current PNG lockup, Teams Marketplace, Sessions/Bots, first-run Models). It is not the blue header + **Gateway ready** page. Setup does not prompt for teams.

## Rules

1. **`Start-DragonAI.vbs`** sets user data under `DragonAIAgent` and launches `start-embedded.ps1`, which opens **DragonAIAgent.exe** only.
2. **Branding / window rename** run only when the exe path is under `DragonAIAgent`. Apply **refuses** any other tree (including standalone Hermes).
3. Dragon connections (`electron-userdata\connections.json`) may make Remote **Embedded Linux** (`http://127.0.0.1:8650`) primary.
4. Standalone `%APPDATA%\Hermes\connections.json` **primary stays local**.
5. Missing desktop copy is a package error: re-download the Dragon zip. Do not tell the user to install Hermes.

Check: `python3 scripts/airmaze/Test-DragonDesktop.py` and `python3 scripts/airmaze/Test-PrivateDesktop.py`.
