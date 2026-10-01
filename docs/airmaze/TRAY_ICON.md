# Tray / taskbar dragon — contain-max (not a pixel bump)

Short design after James: the dragon in the Windows tray / taskbar slot looks too small. Do **not** pick a larger display size (`32px`, `48px`, …). Windows owns the cell (`SM_CXSMICON` / taskbar target size). Fill that cell.

## Rule

**Contain-max:** scale the dragon artwork uniformly so it uses the largest width **and** height that still fit inside the slot. Same as CSS `object-fit: contain` at `width: 100%; height: 100%`.

- No crop of the dragon
- No stretch / distort
- No fixed CSS/pixel display size
- Leftover slot space (if the mark is not square) stays transparent

The circular badge James attached already fills the ICO canvas with **plate + ring**. The dragon inside does not. Treat the near-black field and outer copper ring as empty container, then contain-max the dragon into each embedded frame.

## Where size is set

| Surface | File | What changes |
|---------|------|----------------|
| Running app / taskbar / tray ICO | `installer/winres/icon.ico` (copied over `resources/icon.ico` at launch) | Contain-max frames |
| Shortcut ICO | `branding/dragon-ai-agent-logo.ico` | Contain-max from the navy PNG’s opaque box |
| Rebuild | `python3 branding/tray_icon.py` | Writes both ICOs |

Empty-state `min(22rem, 70%)`, sidebar `32px`, Docker tray-only launch, Bot Screen `:8650` / `dragon-local` do **not** change.

## Embedded ICO sizes

These are the cells Windows may request (100–200% DPI), not a display-size bump. Each frame is contain-maxed independently from the same artwork:

16, 20, 24, 32, 40, 48, 64, 128, 256.

## Out of scope

- Opening Docker Desktop’s dashboard or Dragon `:9119`
- Rebuilding `Hermes.exe` / rewriting `app.asar`
- Merging
