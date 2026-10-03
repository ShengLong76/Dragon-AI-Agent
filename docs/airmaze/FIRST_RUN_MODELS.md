# First-run default chat + image LLMs

Short design for a Dragon AI Agent setup step that writes Hermes gateway config so chat and profile **Generate** work without hand-editing YAML.

Verified against public `NousResearch/hermes-agent` (image-generation docs, `plugins/image_gen/xai`, desktop `avatar-picker.tsx` / `avatar-image.ts`). James’s YAML fragment is the correct **xAI** shape; Hermes also uses a sibling `image_gen.model` key for FAL. We write both.

## Why

Edit profile → Generate shows **“No image model available… Restart gateway”** until the gateway has an image backend. The desktop probes `image.generate` (`probe: true`) on the connected gateway. Chat defaults are easy to miss the same way. First-run should persist both into the **embedded Hermes home** config the Docker volume already mounts (`%USERPROFILE%\.hermes-airmaze-embedded` → `/opt/data`).

## Product defaults (preselected)

| Picker | Default | Hermes keys |
|--------|---------|-------------|
| Default chat LLM | **Grok (xAI)** `grok-4.6` | `principal.provider: xai`, `principal.model: grok-4.6` |
| Default image LLM | **Grok Imagine** `grok-imagine-image` | `image_gen.provider: xai`, `image_gen.model` + `image_gen.xai.model` |

`grok-4.6` is the head of Hermes’s current xAI static catalog (`hermes_cli/models_catalog_static.py`). Older `grok-4` / `grok-4.3` ids still work; retirement maps retired Grok chat ids to `grok-4.3`. The user can change the pickers.

Image quality variants Hermes already lists (surface them):

- `grok-imagine-image` — default, fast
- `grok-imagine-image-quality` — higher fidelity (also the edit fallback)
- `grok-imagine-image-2.0` — typography / layout-aware

## Config shape written

```yaml
principal:
  provider: xai
  model: grok-4.6

image_gen:
  provider: xai
  model: grok-imagine-image
  xai:
    model: grok-imagine-image
```

- **Do not** invent `plugins.image_gen` unless that block already exists (legacy slot). Current Hermes docs and the xAI plugin read **top-level** `image_gen`.
- Merge into an existing `config.yaml`. Do not wipe `bot_desktop`, `browser`, tools, or other keys.
- Do not write API keys. Auth stays Hermes xAI OAuth or `XAI_API_KEY` already on the machine / in the embedded home `.env`.

## UI path

First-run uses the **in-app Models UI** plus launcher `Apply-GatewayModels.ps1 -IfMissing`. Do **not** ship a Desktop / Start Menu **Dragon AI Agent Setup** shortcut. The launch wait window (and its Setup button) is not shown. The WinForms `Onboard-Wizard.ps1` Models step remains in-tree as a deprecated fallback (no product `.lnk`, not auto-launched).

Step order:

`welcome` → **`models`** → `email` → `crm` → `telephony` → `property_data` → `dialer` → `review`

WinForms + console fallback both get two ComboBoxes / numbered lists:

1. Default chat LLM
2. Default image LLM

Copy is **Dragon AI Agent** (not Hermes). Auth line: this step does not ask for a new key; it uses the xAI Grok login Dragon AI Agent already has (OAuth or `XAI_API_KEY`).

- **Continue** writes the selected pair (overwrite those keys).
- **Skip this step** / **Skip wizard** writes the product defaults **only if** `image_gen.provider` or `principal.model` is missing.
- Review lists the chosen labels (never secrets).

Teams picker stays orthogonal and is **not** shown during Setup. Personal Assistant stays the only preinstall. Teams are added later through in-app Teams Marketplace.

## When it lands on disk

Primary file:

`%USERPROFILE%\.hermes-airmaze-embedded\config.yaml`

Launcher writes defaults **before** `docker compose up` when those keys are missing, so a first gateway boot already has Grok Imagine. If the wizard changes the selection after the gateway is up, apply best-effort `docker compose restart` of `hermes-airmaze-gw` (and the serve sidecar). Generate’s own copy still tells the user to restart the gateway if the probe is stale.

## Out of scope

- New OAuth / API-key screens
- Replacing Teams-picker work
- Rebuilding `Hermes.exe` / `app.asar`
- Live UltraDragon smoke in CI (James re-smokes Generate after gateway restart)
- Merging this PR
