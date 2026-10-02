# Plan — onboarding default LLM for all bots

Small plan after `docs/airmaze/BOT_DEFAULT_MODEL.md`. Tests first. Reuse Onboard-Wizard / Apply-GatewayModels / bot profile model fields. Do not invent a second provider stack.

## In scope

1. `gateway_models.py` — persist Hermes `model` beside existing `principal` + `image_gen`; stamp inherited chat model onto bot profiles; skip per-bot overrides.
2. `bot_groups.py` deploy / import — new seats inherit the stored gateway default (product Grok if the gateway file is not there yet).
3. Wizard copy: all bots inherit unless overridden. Review can show the chosen chat id.
4. `Select-BotGroup.ps1` passes `--embedded` so the volume mirror gets the stamp.
5. Docs: this pair, `FIRST_RUN_MODELS.md`, `SETUP_GUIDE.md`, `BOT_GROUPS.md`, README, `DESIGN.md`, `CHANGELOG.md`.
6. `Test-BotDefaultModel.py` plus existing gateway / bot-group / launch-parse checks.

## Tests first (must fail before inherit exists)

- Apply writes gateway `model.default` as well as `principal.model`.
- Apply stamps Personal Assistant under a profiles root to the selected chat model.
- A later team-seat deploy (no model in the pack) inherits the stored default.
- A bot whose `model.default` is a different id and has no inherited marker is left alone.
- `--if-missing` does not overwrite an override or a present principal/model.
- No API keys. Wizard still uses Apply-GatewayModels. `$HermesHome` stays (never `$Home`).
- Syne / crimson branding files are not part of the change.

## Out of scope

- New providers that need keys we do not already use
- Replacing Teams Marketplace
- Merging this PR
