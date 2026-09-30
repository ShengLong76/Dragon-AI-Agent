---
name: understand-dashboard
description: "Open the Understand-Anything dashboard for .ua/knowledge-graph.json. Use only when a human asks for /understand-dashboard. Do not start a first /understand scan unless they also ask for one."
disable-model-invocation: true
argument-hint: "[project-path]"
---

# /understand-dashboard

Open the local Understand-Anything dashboard for this repo's knowledge graph.

## Preconditions

1. Resolve the project directory (`$ARGUMENTS` if it is a path, otherwise the repo root).
2. Prefer `.understand-anything/` only when that directory already exists; otherwise use `.ua/`.
3. If `$UA_DIR/knowledge-graph.json` is missing, **stop**. Tell the human:

   ```text
   No knowledge graph found. Run /understand first (token-heavy first scan; not run during skill install).
   ```

   Do not start `/understand` yourself unless they explicitly ask.

## How to launch

1. If the official plugin is installed, follow its `/understand-dashboard` skill (viewer tarball or Vite dashboard).
2. If the plugin is not installed, point them at Cursor Settings → Plugins → `https://github.com/Egonex-AI/Understand-Anything`, or the no-LLM viewer:

   ```bash
   npx https://github.com/Egonex-AI/Understand-Anything/releases/latest/download/understand-anything-viewer.tgz .
   ```

   The project directory must already contain `.ua/knowledge-graph.json`.
3. Share the full tokenized URL (`http://127.0.0.1:<port>?token=...`) when the server prints it.

See [`docs/airmaze/UNDERSTAND_ANYTHING.md`](../../../../docs/airmaze/UNDERSTAND_ANYTHING.md).
