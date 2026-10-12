/**
 * Dragon AI product version — the number shown next to the logo.
 *
 * Source of truth is `apps/desktop/package.json`, kept in lockstep with
 * `branding/product-feed.json` `productVersion`. Never the Python backend
 * or a git-describe string (those are Hermes-era runtime versions such as
 * `0.21.5+9105`).
 */

import { shortVersion } from '@/lib/version-label'

import packageJson from '../../package.json'

export const DRAGON_PRODUCT_VERSION: string = packageJson.version

export function dragonProductVersionLabel(version: string = DRAGON_PRODUCT_VERSION): string {
  return `v${version.replace(/^v/, '')}`
}

/** True when `version` is this Dragon product, not a foreign runtime. */
export function isDragonProductVersion(version: string | null | undefined): boolean {
  if (!version) {
    return false
  }

  const short = shortVersion(version)

  return short === DRAGON_PRODUCT_VERSION || short.startsWith(`${DRAGON_PRODUCT_VERSION}+`) || short.startsWith(`${DRAGON_PRODUCT_VERSION}-`)
}

/** Product/runtime version safe to paint. Foreign (Hermes) strings become null. */
export function sanitizeRuntimeVersion(version: string | null | undefined): string | null {
  return isDragonProductVersion(version) ? shortVersion(version) : null
}
