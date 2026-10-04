# Plan — first-run chat + image LLM setup

Small plan after `docs/airmaze/FIRST_RUN_MODELS.md`. Tests first. No Electron rebuild. Do not replace Teams-picker work.

## In scope

1. `scripts/airmaze/gateway_models.py` — catalog + merge of `principal`, Hermes `model`, and `image_gen` into Hermes `config.yaml`, then inherit that chat model onto all bot profiles (in-app complete + wizard).
2. `scripts/airmaze/Apply-GatewayModels.ps1` — wizard / launcher wrapper (`--home`, `--chat`, `--image`, `--if-missing`).
3. **In-app first-run Models** is primary: skip auto-launch of WinForms `Onboard-Wizard.ps1`; mark `models=in_app`. Overlay Hermes → Dragon AI copy and expand **Other providers**. Wizard Models step remains for the Setup shortcut (cloud + self-hosted catalog, Grok defaults, Continue `.Text` guard).
4. `start-embedded.ps1` applies product defaults if missing **before** compose up (`-IfMissing` so an in-app provider choice is not overwritten).
5. Installers copy the new scripts + design docs. Install marks in-app onboarding instead of blocking on the wizard.
6. Docs: `SETUP_GUIDE.md`, README onboarding list, `CHANGELOG.md`, one line in `DESIGN.md`.
7. `scripts/airmaze/Test-GatewayModels.py` plus `Test-OnboardWizard.py` (Continue Text guard + Welcome/Models status line + in-app skip).

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
