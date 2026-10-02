# Plan — first-run chat + image LLM setup

Small plan after `docs/airmaze/FIRST_RUN_MODELS.md`. Tests first. No Electron rebuild. Do not replace Teams-picker work.

## In scope

1. `scripts/airmaze/gateway_models.py` — catalog + merge of `principal` and `image_gen` into Hermes `config.yaml` (stdlib only).
2. `scripts/airmaze/Apply-GatewayModels.ps1` — wizard / launcher wrapper (`--home`, `--chat`, `--image`, `--if-missing`).
3. Wizard step `models` after Welcome (WinForms ComboBoxes + console lists). Dragon copy. No new OAuth.
4. `start-embedded.ps1` applies product defaults if missing **before** compose up.
5. Installers copy the new scripts + design docs.
6. Docs: `SETUP_GUIDE.md`, README onboarding list, `CHANGELOG.md`, one line in `DESIGN.md`.
7. `scripts/airmaze/Test-GatewayModels.py` plus `Test-OnboardWizard.py` (Continue Text guard + Welcome/Models status line).

## Tests first (must fail before the engine exists)

- Defaults write `principal.provider=xai`, `principal.model=grok-4.6`, `image_gen.provider=xai`, `image_gen.xai.model=grok-imagine-image`.
- Applying a quality variant writes `grok-imagine-image-quality` / `grok-imagine-image-2.0`.
- Merge keeps an existing `bot_desktop` block.
- `--if-missing` does not overwrite a user `principal.model`.
- No API keys / OAuth tokens written.
- Wizard source shows both pickers, step `models` in the resume order, Dragon AI Agent (not Hermes) copy.
- Existing welcome / Teams / email / DPAPI path still present.

## Out of scope

- Live UltraDragon Generate click
- New providers that need keys we do not already use
- Changing Bot Screen ports / tokens
- Merging PR #10
