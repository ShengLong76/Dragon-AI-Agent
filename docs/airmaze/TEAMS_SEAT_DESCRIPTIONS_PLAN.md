# Plan — Teams Marketplace seat descriptions

After `docs/airmaze/TEAMS_SEAT_DESCRIPTIONS.md`. Tests first. No Electron rebuild. James merges.

## Tasks

1. **Docs** — this file + `TEAMS_SEAT_DESCRIPTIONS.md`. Schema note in `BOT_GROUPS.md`. Teams section in `PRODUCT_BRANDING.md`. `CHANGELOG.md`.
2. **Tests first** — `Test-TeamsPicker.py` (and overlay self-test hooks):
   - Marketing stays Cos’s six ids.
   - SEO Specialist brief is the seoagent.com one-liner; hover detail covers six seats, tools, Autopilot $49, re-apply / `seoagent init`, Buffer / Brevo unchanged.
   - Other Marketing seats have `description` + `descriptionDetail`.
   - `list_teams` / `present_team` expose `bots[]` with those fields.
   - Overlay lists seats under the team name, tooltip on hover/focus, Apply stays on the team (no nested seat buttons).
   - Seat cards use `repeat(4, 1fr)`, `box-shadow`, and a shared `12px` radius.
3. **Schema** — optional `bots[].descriptionDetail`. Pass through `normalize_manifest`, canonical roster fill, and `present_team`.
4. **Copy** — Marketing `bot-group.json` (+ SEO `bot.yaml` brief). Six seats.
5. **UI** — `desktop_branding.py` Teams Marketplace inject + `dragon-ui.css`. User chrome: **Teams Marketplace** under the 32px logo; fade + slight slide/scale; black panel; layered card shadows.
6. **Self-review + PR** against `main`. Do not merge from the agent.

## Verify (Linux CI)

```bash
python3 scripts/airmaze/Test-TeamsPicker.py
python3 scripts/airmaze/Test-BotGroups.py
python3 scripts/airmaze/Test-DesktopBranding.py
```
