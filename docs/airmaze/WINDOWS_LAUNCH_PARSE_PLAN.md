# Plan — Windows launch parse hotfix

Small plan after `docs/airmaze/WINDOWS_LAUNCH_PARSE.md`. Tests first. Encode the UltraDragon hotfix. Do not merge.

## In scope

1. `scripts/airmaze/start-embedded.ps1`
   - Drop PascalCase `OpenUIOnStartupDisabled` from `$patch`.
   - `Start-DragonAIVoiceChat`: `$home` → `$embeddedHome` (and the `--home` argv value).
   - `& $applyModels -HermesHome $data -IfMissing`.
2. `scripts/airmaze/Apply-GatewayModels.ps1` — param `$Home` → `$HermesHome` and every use inside the script.
3. Same-class call sites so the rename does not break setup:
   - `Onboard-Wizard.ps1` (`$home` + `-Home` → `$embeddedHome` + `-HermesHome`)
   - `Apply-VoiceChat.ps1` (`$Home` → `$HermesHome`)
   - `install.ps1` / `DragonAIAgentSetup.ps1` tray `$patch` (single camelCase key)
4. Docs: this pair, one line in `DESIGN.md` / `DOCKER_LAUNCH.md` / `CHANGELOG.md`.
5. Cheap smoke in `scripts/airmaze/Test-LaunchSmoke.py` (and a dedicated parse helper if needed).

## Tests first (must fail on current main)

- Any `*.ps1` tray `$patch` that lists both `openUIOnStartupDisabled` and `OpenUIOnStartupDisabled` fails.
- Any `*.ps1` param `[string]$Home` or assignment `$Home =` / `$home =` fails.
- Launcher must contain `$embeddedHome` and `-HermesHome`.
- `Apply-GatewayModels.ps1` must contain `$HermesHome` and must not contain `[string]$Home`.
- Existing `Test-LaunchSmoke.py` / `Test-GatewayModels.py` / `Test-VoiceChat.py` still pass after the rename.

## Out of scope

- Live UltraDragon shortcut click in CI
- Changing Bot Screen ports / tokens
- Merging this PR
