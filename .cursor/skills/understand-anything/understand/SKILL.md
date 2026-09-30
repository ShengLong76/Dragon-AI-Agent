---
name: understand
description: "Run Understand-Anything /understand to build or refresh .ua/knowledge-graph.json. Use only when a human explicitly asks. Do not start a first-scan LLM analysis automatically — it is token-heavy."
disable-model-invocation: true
argument-hint: "[path] [--full|--auto-update|--no-auto-update|--review|--language <code>|--exclude <globs>]"
---

# /understand

Build or refresh this repo's Understand-Anything knowledge graph.

**Stop unless a human just asked for this command or an explicit first scan.** The initial analysis walks the tree with a multi-agent LLM pipeline and can consume a large number of tokens. James's install of this skill does not include a generated graph.

## Output

- Write the graph under `.ua/` (or keep `.understand-anything/` if that directory already exists).
- Do not `git add` `.ua/`, `.understand-anything/`, or `knowledge-graph.json`.
- Subsequent runs are incremental by default; use `--full` only when asked.

## How to run

1. Confirm a human asked for `/understand` (or "first scan" / "map the codebase with Understand-Anything").
2. If the official plugin is not installed, install it from `https://github.com/Egonex-AI/Understand-Anything` (Cursor Settings → Plugins) and tell the human to re-run `/understand` in a new session. Do not invent a local LLM scan.
3. If the official `/understand` skill from that plugin is available, follow it. Prefer the current working tree as `PROJECT_ROOT`.
4. If the plugin is installed but `/understand` is still missing, say so and point at [`docs/airmaze/UNDERSTAND_ANYTHING.md`](../../../../docs/airmaze/UNDERSTAND_ANYTHING.md).

## After a successful scan

- Tell the human the graph is in `.ua/knowledge-graph.json` and is gitignored.
- They can open it with `/understand-dashboard`.
- Do not commit the graph.
