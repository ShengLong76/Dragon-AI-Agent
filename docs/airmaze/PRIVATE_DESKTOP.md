# Hermes and Dragon AI are separate programs

Short contract after the live UltraDragon fix. Packaging only. No `Hermes.exe` rebuild.

## Paths

| Program | Desktop tree | User data |
|---------|--------------|-----------|
| **Dragon AI Agent** | `%LOCALAPPDATA%\DragonAIAgent\desktop\win-unpacked\Hermes.exe` | `HERMES_DESKTOP_USER_DATA_DIR=%LOCALAPPDATA%\DragonAIAgent\electron-userdata` |
| **Standalone Hermes** | `%LOCALAPPDATA%\hermes\…\win-unpacked\Hermes.exe` (source only) | `%APPDATA%\Hermes` |

Install/start **copy or provision** the unpacked client into the Dragon folder. They never write back into the standalone Hermes tree.

## Rules

1. **`Start-DragonAI.vbs`** sets `HERMES_DESKTOP_USER_DATA_DIR` and launches `start-embedded.ps1`, which opens the **private** client only.
2. **Branding / window rename** run only when the exe path is under `DragonAIAgent`. Apply **refuses** any other tree (including standalone Hermes).
3. Dragon connections (`electron-userdata\connections.json`) may make Remote **Embedded Linux** (`http://127.0.0.1:8650`) primary.
4. Standalone `%APPDATA%\Hermes\connections.json` **primary stays local**.

Check: `python3 scripts/airmaze/Test-PrivateDesktop.py`.
