# Windows launch parse (UltraDragon hotfix)

Short design. James: Desktop / Start Menu **Dragon AI Agent** does nothing. Cos reproduced. `start-embedded.ps1` aborted **before** `Hermes.exe`.

## Why

Three PowerShell parse/runtime rules the launcher violated:

1. **Hashtable keys are case-insensitive.** `$patch` in `Set-DockerTrayOnlySettings` listed both `openUIOnStartupDisabled` and `OpenUIOnStartupDisabled`. Windows PowerShell 5.1 refuses the literal: `Duplicate keys 'OpenUIOnStartupDisabled' are not allowed in hash literals`.
2. **`$HOME` is an automatic, read-only variable.** A function local `$home = ...` or a param `[string]$Home` is the same name. Assignment fails: `Cannot overwrite variable HOME because it is read-only or constant`.
3. **UTF-8 without a BOM is decoded as the ANSI code page.** An em dash (or similar punctuation) inside a double-quoted string becomes garbage that ends the string early (`"Dragon AI Agent - start..."` dies with unexpected token `start`). Prefer ASCII punctuation in `installer/*.ps1` and `scripts/airmaze/*.ps1`. Do not require the user to resave files with a BOM.

Either abort is silent under `Start-DragonAI.vbs` (hidden host). James sees "shortcut does nothing."

## Behavior

| Surface | Rule |
|---------|------|
| Docker settings `$patch` | One key only per hashtable: camelCase `openUIOnStartupDisabled = $true` for `settings.json`. Do not add PascalCase in that same `@{ }`. A separate hashtable may write PascalCase into `settings-store.json`. |
| Installer / launch `.ps1` punctuation | ASCII only (`-`, `...`, `->`). No em dash, en dash, ellipsis, or curly quotes. No UTF-8 BOM requirement. |
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
