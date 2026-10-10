/**
 * Capability carve-outs for an embedded Skills Hub iframe.
 *
 * Dragon's Skills and Plugins hubs are native UI. There is no upstream docs
 * iframe, so no origin is granted clipboard-write or window.open exceptions.
 */

/** @deprecated No hub iframe is embedded; kept so existing call sites compile. */
export const HERMES_HUB_ORIGIN = ''
/** @deprecated No hub iframe is embedded; kept so existing call sites compile. */
export const HERMES_HUB_FALLBACK_ORIGIN = ''

/**
 * Exact-origin membership for a trusted hub frame. Always false: Dragon does
 * not embed the upstream docs picker.
 */
export function isHermesHubOrigin(_origin: string | null | undefined): boolean {
  return false
}

/** The URL schemes a trusted hub frame may delegate to the OS browser. */
const HUB_EXTERNAL_SCHEMES = new Set(['http:', 'https:', 'mailto:'])

/**
 * May a trusted-origin window.open request be handed to the audited external
 * opener? Unused while `isHermesHubOrigin` is false; kept as the protocol
 * gate if a future first-party embed needs the same shape.
 */
export function isHermesHubExternalUrl(url: string): boolean {
  try {
    return HUB_EXTERNAL_SCHEMES.has(new URL(url).protocol)
  } catch {
    return false
  }
}

/**
 * May the requesting frame use the Chromium clipboard-sanitized-write
 * permission? Never: there is no embedded hub frame.
 */
export function isHermesHubClipboardWrite(origin: string | null | undefined): boolean {
  return isHermesHubOrigin(origin)
}
