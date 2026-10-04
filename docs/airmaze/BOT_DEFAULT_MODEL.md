# First-run default LLM applies to all bots

Short design. James: onboarding picks a default LLM provider, and **every bot** uses that model — not only gateway chat / Generate.

Extends [`FIRST_RUN_MODELS.md`](FIRST_RUN_MODELS.md). Same engine (`gateway_models.py`, `Apply-GatewayModels.ps1`). Works for the **in-app** provider connect dialog (primary) and the WinForms Onboard-Wizard edge case. No second provider stack. Syne / crimson untouched.

## Why

`principal` + `image_gen` on the embedded Hermes home make chat and profile Generate work. Hermes **bots are profiles**. Each seat reads `model.provider` / `model.default` (and this repo’s `principal`) from its own `config.yaml`. Leave those unset and the bot does not reliably follow the onboarding pick.

Personal Assistant is applied at install. Team seats land later from Teams Marketplace. Both must inherit the stored default unless the operator overrides that bot.

## Inheritance

| Layer | What is written | When |
|-------|-----------------|------|
| Gateway home `config.yaml` | Existing `principal` + `image_gen`, plus Hermes `model.provider` / `model.default` | In-app provider complete (discover Hermes config + sync). Wizard Continue (overwrite those keys). Skip / launch `--if-missing` only if chat or image is absent. |
| Each bot profile | Same chat provider/model on `config.yaml` (create if missing), and on existing `profile.yaml` / `bot.yaml` | After gateway write (PA already on disk). Again on deploy/import of a group (later seats). In-app complete POSTs `http://127.0.0.1:8655/api/inherit-models`. |
| Per-bot override | A `model` / `principal.model` **without** `# dragon-ai-inherited-model` that is not the stored default | Left alone. Wizard re-run, in-app re-inherit, and re-deploy do not clobber it. |

Suggested picker defaults stay **Grok (xAI) `grok-4.7`** and **Grok Imagine** `grok-imagine-image`. Whatever the operator actually selects becomes the stored default.

Marker on inherited files:

```yaml
# dragon-ai-inherited-model
principal:
  provider: xai
  model: grok-4.7
model:
  provider: xai
  default: grok-4.7
```

Hermes profile field is `model` (see upstream `_read_config_model`). `principal` stays so this repo’s gateway shape and bots stay one stack. Image generation stays gateway `image_gen` (Generate probe). Do not write API keys.

## In-app path (primary)

The first-run Models dialog is Hermes’s provider connect UI. When it completes (dialog gone / “not connected” cleared / a provider row clicked), `provider-setup.js` POSTs the inherit helper. The helper reads the newest Hermes `config.yaml` that already has a chat model (embedded home, `%LOCALAPPDATA%\hermes`, `~\.hermes`), writes that pair onto the embedded gateway if needed, and stamps every deployed bot. Launch also runs `gateway_models.py inherit` and serves `:8655`.

## Paths

- Gateway: `%USERPROFILE%\.hermes-airmaze-embedded\config.yaml`
- Desktop bots: `%LOCALAPPDATA%\hermes\profiles\<bot-id>\`
- Embedded mirror: `%USERPROFILE%\.hermes-airmaze-embedded\profiles\<bot-id>\`

Deploy reads the gateway file (or product Grok defaults if it is missing) and stamps new seats. `Select-BotGroup` passes `--embedded` so Bot Screen sees the same model without waiting for the next launch mirror.

## Out of scope

- New OAuth / API-key screens or a second catalog
- Changing Syne, crimson, or overlay chrome
- Rebuilding `Hermes.exe` / `app.asar`
- Live UltraDragon click in CI
- Merging this PR
