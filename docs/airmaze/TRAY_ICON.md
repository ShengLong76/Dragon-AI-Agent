# Tray / taskbar dragon — contain-max the sidebar mark

Short design after James: PR #12 (`be015b0`) contain-maxed the **circular copper badge**. That was not finished. Isolating the badge punches the plate but leaves a copper rim, so the dragon still looks small / unfinished in the Windows slot. The apply path also preferred `installer/winres/icon.ico`, which the installer never copies into `%LOCALAPPDATA%\DragonAIAgent\`, so UltraDragon often never received the new frames.

## Rule

**Contain-max:** scale the dragon artwork uniformly so it uses the largest width **and** height that still fit inside the slot. Same as CSS `object-fit: contain` at `width: 100%; height: 100%`.

- No crop of the dragon
- No stretch / distort
- No fixed CSS/pixel display size (`32px`, `48px`, …)
- Leftover slot space (if the mark is not square) stays transparent

**Source:** the transparent low-poly sidebar mark (`branding/dragon-ai-agent-logo.png` / SVG). Navy body `#314A73`, red eyes, no plate, no copper ring. That mark already reads larger and cleaner at 16–32px than the circular badge. Taskbar, tray, Setup.exe, and Desktop / Start Menu shortcuts share **one** ICO.

Windows owns the cell (`SM_CXSMICON` / taskbar target size). Do not pick a display size.

## Where size is set

| Surface | File | What changes |
|---------|------|----------------|
| Running app / taskbar / tray ICO | `installer/winres/icon.ico` | Contain-max frames from the sidebar mark |
| Shortcut ICO | `branding/dragon-ai-agent-logo.ico` | **Same bytes** as the winres ICO |
| Rebuild | `python3 branding/tray_icon.py` | Writes both ICOs from the sidebar PNG |
| Live apply | `Apply-DesktopBranding.ps1` / `stamp_app_icon` | Copies that ICO onto Hermes resource paths |

Empty-state `min(22rem, 70%)`, sidebar `32px`, Docker tray-only launch, Bot Screen `:8650` / `dragon-local` do **not** change.

## Apply path (must actually land)

Every launch, with `-ExePath` pointing at on-disk `Hermes.exe`, copy the sidebar ICO over:

- `{exeDir}\resources\icon.ico` (create `resources` if needed)
- `{exeDir}\icon.ico`
- `{exeDir}\resources\app\icon.ico` when that folder exists
- `{exeDir}\resources\app.asar.unpacked\icon.ico` when that folder exists
- any other existing `icon.ico` under `{exeDir}\resources` (skip `node_modules`)

Prefer `branding\dragon-ai-agent-logo.ico` (the file the installer already ships). Fall back to `installer\winres\icon.ico`. The installer must also copy `installer\winres\icon.ico` into the install root so both candidates exist on UltraDragon.

PE stamp of `Hermes.exe` is best-effort (`rcedit` on PATH). Failure is non-fatal.

Desktop / Start Menu `.lnk` `IconLocation` must be rewritten to the same ICO even when the shortcut already targets `wscript.exe` + `Start-DragonAI.vbs`.

## How Cos tips UltraDragon live

1. Close `Hermes.exe` (icon files lock while the process is up).
2. Copy this revision into `%LOCALAPPDATA%\DragonAIAgent\` (or re-run Setup). Confirm both `branding\dragon-ai-agent-logo.ico` and `installer\winres\icon.ico` are the new files.
3. Open Start Menu **Dragon AI Agent**. Launch runs apply before the window opens and refreshes shortcut icons.
4. If the taskbar / shortcut still shows the old mark, Windows cached the ICO: sign out / restart Explorer, or delete `%LOCALAPPDATA%\IconCache.db` and the `Explorer\iconcache_*.db` files under `%LOCALAPPDATA%\Microsoft\Windows\Explorer\`, then restart Explorer. Do **not** pick a 48px display size as a workaround.

## Embedded ICO sizes

These are the cells Windows may request (100–200% DPI), not a display-size bump. Each frame is contain-maxed independently from the same artwork:

16, 20, 24, 32, 40, 48, 64, 128, 256.

## Out of scope

- Opening Docker Desktop’s dashboard or Dragon `:9119`
- Rebuilding `Hermes.exe` / rewriting `app.asar` (PE stamp is best-effort only)
- Merging
