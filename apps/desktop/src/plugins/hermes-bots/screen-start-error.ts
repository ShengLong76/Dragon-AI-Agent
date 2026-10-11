/** Map a raw `display.start` failure to copy the Computer pane can show. */

const LEFTOVER_DISPLAY = /already active for display|xvnc exited during startup|\.x\d+-lock|leftover display|fatal server error/i

/** The RPC never delivered the backend reason: heartbeat died or the 30s
 *  default deadline fired while `display.start` was blocked on docker. */
const OPAQUE_GATEWAY = /gateway connection closed|gateway is not connected|request timed out|heartbeat acknowledgement timed out|websocket closed|could not connect to .+ gateway/i

export function isLeftoverDisplayError(raw: string): boolean {
  return LEFTOVER_DISPLAY.test(raw)
}

export function isOpaqueGatewayStartError(raw: string): boolean {
  return OPAQUE_GATEWAY.test(raw)
}

export function friendlyScreenStartError(
  raw: string,
  leftoverCopy: string,
  opaqueGatewayCopy?: string
): string {
  const text = raw.trim()
  if (!text) {
    return leftoverCopy
  }
  if (isLeftoverDisplayError(text)) {
    return leftoverCopy
  }
  if (opaqueGatewayCopy && isOpaqueGatewayStartError(text)) {
    return opaqueGatewayCopy
  }
  return text
}
