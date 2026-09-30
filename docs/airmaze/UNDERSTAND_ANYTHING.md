# Understand Anything

James asked to add the MIT [Understand-Anything](https://github.com/Egonex-AI/Understand-Anything) tool so Cursor and future cloud agents can map this repo.

This checkout vendors a **Cursor skill + plugin entry**, not a generated knowledge graph. A first `/understand` scan is token-heavy and was **not** run as part of the install.

## What was added

| Path | Role |
|------|------|
| `.cursor/skills/understand-anything/` | Project skill pointer (MIT; no paid extras) |
| `.cursor/skills/understand-anything/understand/` | `/understand` |
| `.cursor/skills/understand-anything/understand-dashboard/` | `/understand-dashboard` |
| `.cursor-plugin/plugin.json` | Cursor plugin manifest pointing at those skills |
| `.gitignore` | Ignores `.ua/` and legacy `.understand-anything/` |

License stays MIT. See `THIRD_PARTY_NOTICES.md` and `.cursor/skills/understand-anything/LICENSE`.

## How to run the first scan later

1. In Cursor: **Settings → Plugins** → paste `https://github.com/Egonex-AI/Understand-Anything` → install **understand-anything**.
2. In Agent chat, run:

   ```text
   /understand
   ```

   Optional: `/understand --language en` or scope a subdirectory (`/understand scripts`).

3. The pipeline writes `.ua/knowledge-graph.json` (or keeps `.understand-anything/` if that directory already exists).
4. Open the graph:

   ```text
   /understand-dashboard
   ```

The first scan analyzes the whole tree and can use a large number of tokens. Later `/understand` runs are incremental by default.

Do **not** commit `.ua/` or `knowledge-graph.json`. They are gitignored.

## Viewer without a new LLM scan

After a graph exists on disk:

```bash
npx https://github.com/Egonex-AI/Understand-Anything/releases/latest/download/understand-anything-viewer.tgz .
```

## Out of scope

This install does not change Dragon branding, the dragon logo, Syne, overlay CSS, Bot Screen (`127.0.0.1:8650`, `dragon-local`, `hermes-airmaze-gw` / `hermes-airmaze-desktop`), or `app.asar`.
