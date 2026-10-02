# Windows launch parse (UltraDragon hotfix)

Short design. James: Desktop / Start Menu **Dragon AI Agent** does nothing. Cos reproduced. `start-embedded.ps1` aborted **before** `Hermes.exe`.

## Why

Two PowerShell parse/runtime rules the launcher violated:

1. **Hashtable keys are case-insensitive.** `$patch` in `Set-DockerTrayOnlySettings` listed both `openUIOnStartupDisabled` and `OpenUIOnStartupDisabled`. Windows PowerShell 5.1 refuses the literal: `Duplicate keys 'OpenUIOnStartupDisabled' are not allowed in hash literals`.
2. **`$HOME` is an automatic, read-only variable.** A function local `$home = …` or a param `[string]$Home` is the same name. Assignment fails: `Cannot overwrite variable HOME because it is read-only or constant`.

Either abort is silent under `Start-DragonAI.vbs` (hidden host). James sees “shortcut does nothing.”

## Behavior

| Surface | Rule |
|---------|------|
| Docker tray `$patch` | One key only: camelCase `openUIOnStartupDisabled = $true`. Do not add PascalCase. JSON on disk still gets that one name via `Add-Member`. |
| Embedded Hermes data dir | Call it `$embeddedHome` / `-HermesHome`. Never `$home` / `$Home` / `-Home`. |
| `Apply-GatewayModels.ps1` | Param `[string]$HermesHome` (not `$Home`). Wrapper still forwards Python `--home`. |
| Python engines | Keep `--home` (argparse on `gateway_models.py` / `voice_chat.py`). That string is not a PowerShell variable. |
| Call sites | `start-embedded.ps1` and `Onboard-Wizard.ps1` pass `-HermesHome`. |

Same two bugs exist on the install and wizard paths (`install.ps1`, `DragonAIAgentSetup.ps1`, `Apply-VoiceChat.ps1`, `Onboard-Wizard.ps1`). Fix those in the same change so the next install/setup does not hit the same abort.

## Out of scope

- Changing Docker Desktop JSON schema or starting the Containers dashboard
- Renaming the Python `--home` CLI
- Live UltraDragon click after merge (James/Cos re-smoke the shortcut)
- Merging this PR
