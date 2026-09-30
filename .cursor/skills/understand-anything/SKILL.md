---
name: understand-anything
description: "Project pointer for the MIT Understand-Anything plugin. Use only when a human explicitly asks to map this repo, run /understand, or open /understand-dashboard. Do not start a first-scan LLM analysis on your own — it is token-heavy."
disable-model-invocation: true
---

# Understand Anything (vendored pointer)

This repo vendors the [Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) tool the same way other Cursor skills live under `.cursor/skills/`: a project skill plus a `.cursor-plugin/plugin.json` entry.

It does **not** vendor the official multi-agent pipeline, dashboard packages, or paid extras. The first `/understand` scan of this tree is token-heavy and must not run unless a human asks.

## Slash commands

| Command | When to use |
|---------|-------------|
| `/understand` | First or incremental knowledge-graph scan. Writes `.ua/`. |
| `/understand-dashboard` | Open the local graph dashboard. Needs `.ua/knowledge-graph.json`. |

See [`docs/airmaze/UNDERSTAND_ANYTHING.md`](../../../docs/airmaze/UNDERSTAND_ANYTHING.md).

## Rules for agents

1. **Do not run a first scan** unless a human explicitly asks for `/understand` or a knowledge-graph map.
2. **Do not commit** `.ua/` or `.understand-anything/` (gitignored).
3. **Do not change** Dragon branding, the dragon logo, Syne, overlay CSS, Bot Screen (`127.0.0.1:8650`, token `dragon-local`, images `hermes-airmaze-gw` / `hermes-airmaze-desktop`), or rewrite `app.asar`.
4. Keep this product **MIT**. Do not vendor paid Understand-Anything extras.

## Install the official plugin (when a human wants the full tool)

Cursor:

1. **Cursor Settings → Plugins**
2. Paste `https://github.com/Egonex-AI/Understand-Anything`
3. Add / install **understand-anything**
4. Restart the agent session if slash commands do not appear

Claude Code (optional):

```text
/plugin marketplace add Egonex-AI/Understand-Anything
/plugin install understand-anything
```

Local clone (optional; not required for this pointer):

```bash
git clone https://github.com/Egonex-AI/Understand-Anything.git ~/.understand-anything/repo
```

## Graph location

- Preferred data dir: `.ua/`
- Legacy data dir (only if already present): `.understand-anything/`
- Primary artifact: `.ua/knowledge-graph.json`

Both data dirs are gitignored in this repo.
