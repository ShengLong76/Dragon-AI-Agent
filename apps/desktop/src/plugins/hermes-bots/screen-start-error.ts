/** Map a raw `display.start` failure to copy the Computer pane can show. */

const LEFTOVER_DISPLAY = /already active for display|xvnc exited during startup|\.x\d+-lock|leftover display|fatal server error/i

export function isLeftoverDisplayError(raw: string): boolean {
  return LEFTOVER_DISPLAY.test(raw)
}

export function friendlyScreenStartError(raw: string, leftoverCopy: string): string {
  const text = raw.trim()

  if (!text) {
    return leftoverCopy
  }

  return isLeftoverDisplayError(text) ? leftoverCopy : text
}
