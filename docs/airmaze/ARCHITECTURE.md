# Dragon AI Agent Architecture — Embedded Bot Screen on Windows

**Template packaging.** Profile catalog may include business packs (e.g. real estate). Design goal: give Dragon AI Agent a Bot Screen (TigerVNC + Xfce Linux desktop) that the Windows agent desktop client can watch and take over, **without** requiring a second physical/cloud Linux gateway box for day-to-day local work.

---

## Problem

Upstream Bot Screen is **Linux-gateway-only**. macOS and Windows agent hosts keep their real display; the Screen pane is not offered on those OS hosts. TigerVNC `Xvnc` + Xfce run on the gateway (or inside its terminal sandbox). A pure Windows UltraDragon install therefore cannot host Bot Screen natively.

Dragon AI Agent needs the pane anyway: watch the bot, take over for login/2FA/CAPTCHA, hand control back.

---

## Primary design (preferred)

```
┌─────────────────────────────────────────────────────────────┐
│ UltraDragon (Windows)                                       │
│                                                             │
│  ┌──────────────────────┐     localhost      ┌────────────┐ │
│  │ agent desktop client       │◄──────────────────►│ Embedded   │ │
│  │ (Windows client)     │  gateway API :8642 │ gateway    │ │
│  │                      │  dashboard   :9119 │ container  │ │
│  │  Bot Screen pane     │  /api/display/ws   │ (Linux)    │ │
│  │  (noVNC via gateway) │                    │ TigerVNC   │ │
│  └──────────────────────┘                    │ + Xfce     │ │
│                                              │ + Chromium │ │
│                                              └────────────┘ │
│                       Docker Desktop Linux engine            │
└─────────────────────────────────────────────────────────────┘
```

### Slice 1 (now) — Docker Desktop Linux engine

1. Run Docker Desktop on UltraDragon with the Linux (WSL2) engine.
2. Pull and run a **desktop-capable** official image:
   - Gateway with packages baked in: `nousresearch/hermes-agent:*-desktop` (e.g. `:latest-desktop`, `:v*-desktop`)
   - Or slim gateway + sandbox desktop: terminal backend `docker` with `nousresearch/hermes-sandbox:desktop`
3. Publish only loopback-friendly host ports (see `EMBEDDED_GATEWAY.md` / `docker-compose.embedded.yml`).
4. Configure the agent desktop client’s Remote gateway to `127.0.0.1` (same machine). The Screen pane talks to the Linux container’s gateway over the normal authenticated connection; no raw VNC TCP.

**Why first:** lowest friction, official images already ship `-desktop` tags and `hermes-sandbox:desktop`, matches upstream “where the screen runs” model, keeps Dragon AI Agent changes in config + docs until UltraDragon can clone.

### Slice 2 (later) — microVM

If Docker Desktop / WSL2 proves too coarse (isolation, GPU, lifecycle), embed a small Linux microVM (e.g. Hyper-V / Firecracker-class guest) that runs the same gateway + Bot Screen stack. Desktop still connects to a localhost gateway endpoint. Same UX; stronger boundary than a shared Docker Desktop VM.

Defer until Slice 1 proves the product loop.

---

## Alternate path — Proxmox Windows VMs

Keep existing Proxmox-hosted Windows VMs as a **fallback** when:

- UltraDragon is offline, or
- Operators prefer a full Windows guest beside a dedicated Linux gateway VM on Proxmox.

In that layout, agent desktop client (Windows VM) talks to a separate Linux gateway VM on the lab network (or Tailscale), not to an embedded container. Dragon AI Agent should treat this as compatible ops, not the default local-dev story.

| Path | Gateway location | Bot Screen host | When |
|------|------------------|-----------------|------|
| **Preferred** | Docker Desktop container on UltraDragon | Same Linux container (or its docker sandbox) | Local Dragon AI Agent work |
| **Later** | microVM on UltraDragon | Guest Linux | Stronger isolation |
| **Alternate** | Proxmox Linux VM | That VM | Lab / offline UltraDragon |

---

## Non-goals (this template)

- No CRM, listings, or real-estate skills in the fork by default.
- No public GitHub fork or push remotes.
- No Cos-box clone of hermes-agent (policy).
- No requirement to rewrite upstream Bot Screen for native Windows display.

---

## Config intent (conceptual)

- Windows client: Remote gateway → `127.0.0.1` (embedded).
- Container: `bot_desktop` enabled; prefer `-desktop` image so Install-on-host is unnecessary.
- Optional: `terminal.backend: docker` + `docker_image: nousresearch/hermes-sandbox:desktop` so screen + shell share the sandbox boundary.
- Secrets stay in the operator’s local Hermes home volume (`%USERPROFILE%\.hermes` or container `/opt/data`) — never in this package.

---

## Success for Slice 1

1. Bootstrap script creates local fork under `%LOCALAPPDATA%\hermes\hermes-airmaze`.
2. `docker compose … up` brings a desktop-tagged gateway on localhost.
3. agent desktop client connects to that gateway and shows Start screen / live Bot Screen.
4. Take over / hand back works for a headed browser login flow.

Details: `EMBEDDED_GATEWAY.md`. Upstream map: `UPSTREAM_NOTES.md`.

---

## Packaging note (v0.1.0)

Distribution lives in `ShengLong76/airmaze-agent` (this packaging repo). Windows `DragonAIAgentSetup` provisions WSL2/Docker best-effort, suppresses Docker dashboard on startup (tray-only), brings up the embedded gateway, and installs the Personal Assistant profile. The desktop client remains a separate install when missing (on-disk `Hermes.exe`; display name Dragon AI Agent — see `BRANDING.md`).
