# Dragon AI Agent — product branding gaps (2026-10-01)

Short design after James’s UltraDragon notes. Packaging overlay only. No Electron rebuild. No `app.asar` rewrite. Bot Screen stays `127.0.0.1:8650` / `dragon-local` / `hermes-airmaze-gw` / `hermes-airmaze-desktop`.

This note agrees the three surfaces before code. Plan: `docs/airmaze/PRODUCT_BRANDING_PLAN.md`.

## What James marked

1. **Sidebar header is empty.** Red box on the top-left rail, above SESSIONS / BOTS: “Add Logo and name.”
2. **Taskbar / running app icon is still Hermes.** Purple rounded square with two white dots. Shortcuts may already point at a Dragon ICO; the process is still `Hermes.exe`.
3. **A Hermes bot is still in BOTS and cannot be deleted.** Prefer exclude, not “make deletable.” No Hermes bot on a clean install. Migration must drop an existing Hermes profile so it does not come back (including a zombie under UNASSIGNED).

PR #3 / #7 already overlay empty-state copy, Syne, the navy mark, and a CSS hide of `[data-roster-key$="::default"]`. That hide is not enough: the built-in `default` profile is labeled Hermes in `labels.ts`, leftover folders under `%LOCALAPPDATA%\hermes\profiles\` still enumerate, and `Hermes.exe` still carries the upstream PE icon.

## Mark and name

- **In-app mark:** the existing navy coiled dragon (`branding/dragon-ai-agent-logo.png`). No new logo. Empty-state and sidebar header stay navy / unboxed.
- **Windows ICO:** the circular Dragon badge James attached (`installer/winres/icon-source.png` → contain-max `installer/winres/icon.ico`). That is the Setup.exe icon and the asset for taskbar / Start Menu / `Hermes.exe` stamp. Do not invent a third mark. Do not pick a fixed display pixel size — contain-max the dragon into the Windows slot (`docs/airmaze/TRAY_ICON.md`).
- **Name in the rail:** **Dragon AI** (fits the 16rem sidebar). Accessible name **Dragon AI Agent** (matches empty-state / settings copy).
- **Type:** Syne 700, foreground `#F0F0F5` on `#1C1C20` (≥4.5:1). Sidebar / chat / Teams Marketplace overlay type matches Grok Bot: **16px** body, **14px** chrome, muted `#C4C4CE` (not Hermes 13px / 54% grey). Logo beside the name is decorative (`aria-hidden="true"`), the transparent SVG mark (no red border, no plate), height matched to the Teams Marketplace button (fixed 32px). The Marketplace control sits under the logo. Host fallback: `docs/airmaze/SIDEBAR_HOST.md`.

UI UX Pro Max: decorative-beside-text (`aria-hidden`); Color Contrast (High). No verified “sidebar brand lockup” row — general guidance only: keep the lockup out of the SESSIONS / BOTS tab hit targets.

## 1) Sidebar header

Upstream chrome *defined* `data-slot="sidebar-header"` / `sidebar-inner`. Live UltraDragon Hermes does not paint those — only `sidebar-wrapper`, and that node is the full app shell.

**Do:** at overlay time, inject a brand lockup (CSS + `sidebar-header.js` / `teams-picker.js`). Try column hosts first (`sidebar-header`, `sidebar-inner`, `sidebar-container`, `sidebar`). If those are absent, mount a body overlay `[data-dragon-ai-sidebar-fixed]` **below** the Sessions / Bots strip so those tabs stay visible and clickable. Do **not** treat `sidebar-wrapper` as a column. Design: `docs/airmaze/SIDEBAR_HOST.md`.

Do not cover SESSIONS / BOTS. Do not restyle Bot Screen.

## 2) Running app / taskbar / Start Menu icon

`Hermes.exe` is stamped with the Hermes ICO by upstream `rcedit` (`set-exe-identity.mjs`). Extra resource `resources/icon.ico` is the same. Launching the exe (not the `.lnk`) makes the taskbar use that PE icon. Product `.lnk` files already set `IconLocation` to the Dragon ICO; that does not re-icon the running process.

**Do (every launch, idempotent):**

1. Copy `dragon-ai-agent-logo.ico` over `resources/icon.ico` next to the exe (and any other unpacked `icon.ico` beside it).
2. Stamp `Hermes.exe` PE icon resources with that ICO when a stamper is available (`rcedit` on PATH, or a small Python/PE helper). Failure is non-fatal (log + continue) so a missing stamper never blocks boot.
3. Keep Desktop / Start Menu **Dragon AI Agent** `.lnk` `IconLocation` on the Dragon ICO.
4. Set `System.AppUserModel.ID` on `Dragon AI Agent Client.lnk` to the upstream id `com.nousresearch.hermes` so Windows can show the shortcut icon for that process when the PE stamp does not stick.

Do not rename `Hermes.exe`. Do not rewrite `app.asar`.

## 3) Exclude Hermes from BOTS (not hide)

James: do **not** ship a Hermes bot. Not “make it deletable.”

The roster row labeled Hermes is the reserved profile id `default` (`return 'Hermes'` when `bot.name === 'default'` and there is no title). A leftover folder `%LOCALAPPDATA%\hermes\profiles\hermes` or `profiles\default` also enumerates and often lands under UNASSIGNED. UI delete cannot clear the reserved root profile. CSS `display:none` leaves a zombie.

**Exclude list (folder names / roster ids, case-insensitive):** `default`, `hermes`.

**Do:**

1. **Purge on install and every launch** (before the client opens, and when mirroring into the embedded volume): delete those folders from `%LOCALAPPDATA%\hermes\profiles\` and `%USERPROFILE%\.hermes-airmaze-embedded\profiles\`. Do not delete `personal-assistant` or other catalog bots.
2. **Never recreate them.** Deploy / import / sync skip those ids. Catalog stays Personal Assistant + Real Estate only.
3. **Overlay:** keep the CSS hide as a backstop; also drop `return 'Hermes'` (already blank). Do not seed a default Hermes profile.
4. **Docs:** migration for an existing UltraDragon box — delete the two folders, relaunch. If the reserved gateway home still enumerates `default`, the overlay hide remains the UI backstop; we do not wipe `$HERMES_HOME` itself (that would break the gateway).

Personal Assistant stays the user-facing bot.

## 4) Named BOTS section on import / deploy (not UNASSIGNED)

James: when a **bot group / profile** is imported, those bots must sit in a **named group in the Dragon AI UI**, labeled with the pack display name (e.g. “Marketing Team”, “Real Estate Cold Call Lead Refresher”, “Trading Team”). They must not land under **UNASSIGNED**.

Upstream BOTS sections (`apps/desktop/src/plugins/hermes-bots/user-sections.ts`):

- The section **list** is local plugin storage (`bot-sections-v1` = `[{ id, name }]`).
- **Membership lives on the bot**, not on the section: `profile.yaml` → `ui_meta.hermes-bots.sectionId` + `sectionName`.
- **UNASSIGNED** is whatever has no valid `sectionId`. It is not a section you can write.
- `adoptBotSectionsFromMeta` rebuilds a section the local list has never seen when every member carries **both** id and name. That is how another desktop (or a packaging overlay) files bots without clicking “New section”.

**Do (deploy, import, Apply-Profile / Import-Profile shims, re-apply of an existing pack):**

1. Stable section id: `sec-dragon-<group-id>` (so re-apply updates the same folder, not a second one).
2. Section label: the group `name` / leftover profile `displayName`.
3. Stamp `sectionId` + `sectionName` (+ title) on each bot’s `profile.yaml` `ui_meta.hermes-bots` and on `bot.meta.json`.
4. Mirror the stamped `profile.yaml` into the embedded volume so Bot Screen / Remote see the same filing.

Singular one-bot import (toggle on) does **not** invent a department section — that bot stays unassigned unless it already had one.

Do not restyle the BOTS pane. Do not invent a second groups UI. The upstream section chrome is the product surface.

## 5) In-app Teams Marketplace (not PowerShell-only)

James: pick a bot team from the **Dragon AI UI** (sidebar / first-run / settings-adjacent), not only `Import-Profile.ps1`.

Built-in Teams Marketplace (one click): **Real Estate Lead Gen**, **Marketing Team**, **Trading Team** — multi-bot packs only. **Personal Assistant** is the default single-bot profile (preinstalled); it is not a team. Apply files those bots under that display name — not Unassigned. Each seat shows `description` under the name; `descriptionDetail` pops on hover/focus (Marketing seats ship both; SEO Specialist is the seoagent.com write-up). **Import from file** stays for custom zip/JSON. Design: `docs/airmaze/TEAMS_SEAT_DESCRIPTIONS.md`.

**Do (packaging overlay; no Electron rebuild):**

1. Inject a **Teams Marketplace** button + dialog into the unpacked desktop client (`desktop_branding.py` / `dragon-ui.css`). The user-visible control label is **Teams Marketplace** (not “Teams”). The control sits under the 32px logo; the panel is black and opens with a fade + slight slide/scale.
2. Loopback helper `teams_picker.py` on `127.0.0.1:8653` (`GET /api/teams`, `POST /api/teams/apply`, `POST /api/teams/import`). Not Bot Screen `:8650`.
3. Launch starts the helper (`start-embedded.ps1`). First-run wizard has **Teams Marketplace**. `Select-BotGroup.ps1` window title is **Teams Marketplace**; Import file remains.
4. Helper always unions the bundled catalog so Marketing / Trading show even if GitHub is stale.

Do not add a Hermes team. Do not restyle Bot Screen.

## Out of scope

- Rebuilding `Hermes.exe` / rewriting `app.asar`
- Changing ports, tokens, image names, or license attribution
- Inventing a new logo
- Live UltraDragon installs (verify steps only)
- Merging (James merges)
- Piling onto draft PR #9
