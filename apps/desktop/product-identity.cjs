// The desktop product identity — THE single source for every name-shaped
// value a variant owns. HERMES_DESKTOP_VARIANT=light builds "Dragon AI
// Light", the remote-only client; everything else is full "Dragon AI".
//
// Consumed at build time by electron-builder.config.cjs (packaging
// identity). electron/product-identity.ts is the typed runtime accessor.
// @ts-check
/// <reference types="node" />
'use strict'

const variants = {
  '': { display: 'Dragon AI', kebab: 'dragon-ai-claude', pascal: 'DragonAIClaude' },
  light: {
    display: 'Dragon AI Light',
    kebab: 'dragon-ai-claude-light',
    pascal: 'DragonAIClaudeLight'
  },
  bundled: {
    display: 'Dragon AI Agent',
    kebab: 'dragon-ai-claude-bundled',
    pascal: 'DragonAIClaudeBundled'
  }
}

const variant = process.env.HERMES_DESKTOP_VARIANT || ''
if (!['', 'light', 'bundled', 'store'].includes(variant)) {
  throw new Error(`Unknown HERMES_DESKTOP_VARIANT ${variant}. expected one of (empty), light, bundled, store`)
}

// 'store' is a Store-submission packaging identity layered on the bundled
// variant: same Electron app (displayName/appId/appNamePascal -> shared
// userData + single-instance lock with the out-of-store install), different
// MSIX package identity. The Store re-signs on submission.
const store = variant === 'store'
const light = variant === 'light'
const name = variants[store ? 'bundled' : (variant || '')]

// The electron-updater feed channel this build PUBLISHES to. A canary
// tag (vX.Y.Z+canary.YYYYMMDDTHHMMSSZ) writes canary.yml / light-canary.yml;
// stable tags write latest.yml / light.yml. Keyed on the payload tag so
// the one release workflow serves both channels — a canary build can
// never overwrite the stable feed file, and vice versa.
const canary = /\+canary\.20\d{6}T\d{6}Z$/.test(process.env.HERMES_PAYLOAD_TAG || '')

// Nonstable installs own their package family and local desktop state. The
// seven-character commit suffix also names the CLI and fits MSIX's name cap.
const buildCommitEnv = process.env.HERMES_BUILD_COMMIT || ''
const buildCommit = /^[a-f0-9]{40}$/.test(buildCommitEnv) ? buildCommitEnv.slice(0, 7) : null
const displayName = buildCommit
  ? `${name.display} ${buildCommit}`
  : canary
    ? `${name.display} Canary`
    : name.display

const kebabSuffix = buildCommit ? `-${buildCommit}` : canary ? '-canary' : ''
const pascalSuffix = buildCommit ? `Commit${buildCommit}` : canary ? 'Canary' : ''
const cliName = `${light ? 'dragon-light' : 'dragon'}${kebabSuffix}`
if (store && (canary || buildCommit)) {
  throw new Error('Store packaging is only eligible for stable releases')
}

// NSIS uninstall GUID of the existing Dragon AI install. electron-builder
// otherwise derives a new GUID from a flavored appId, so a commit/canary
// build registers a second app instead of upgrading in place.
const WINDOWS_NSIS_GUID = 'b3558a90-7aa1-5a89-862f-0f6a264a6466'

/** @typedef {import("./product-identity.d.cts")} ProductIdentity */

/** @type {ProductIdentity} */
const identity = {
  store,
  light,
  displayName,
  appId: `ai.dragon.${name.kebab}${kebabSuffix}`,
  // Store and commit builds do not publish a release feed.
  channel: store || buildCommit ? null : light ? (canary ? 'light-canary' : 'light') : (canary ? 'canary' : 'latest'),
  appNamePascal: `${name.pascal}${pascalSuffix}`,
  artifactNamePascal: name.pascal,
  windowsExecutableName: kebabSuffix ? cliName : displayName,
  cliName,
  msixAppIdWithOrg: `DragonAI.${name.pascal}${pascalSuffix}`,
  nsisGuid: WINDOWS_NSIS_GUID,
  ...(store
    ? {
        storeMsix: {
          // Partner Center publisher identity (the account's publisher ID) —
          // validated + re-signed by the Store on submission.
          identityName: 'DragonAI.DragonAIClaude',
          publisher: 'CN=EE6D86E4-606F-4E38-B940-AD7248C9D519',
          publisherDisplayName: 'Dragon AI'
        }
      }
    : {})
}

/**
 * Windows desktop builds share one install identity so NSIS upgrades in place.
 * Commit/canary/channel flavor stays in the version string, icon badge, and
 * About screen — never in appId, product name, exe, or %APPDATA%.
 *
 * @param {ProductIdentity} current
 * @param {string} [platform]
 * @returns {ProductIdentity}
 */
function finalizeIdentity(current, platform = process.platform) {
  const withGuid = { ...current, nsisGuid: WINDOWS_NSIS_GUID }
  if (platform !== 'win32') {
    return withGuid
  }

  // Keep appNamePascal aligned with artifactNamePascal so applyDesktopIdentity
  // does not pin a per-flavor folder. Electron then keeps the historical
  // %APPDATA%/Dragon AI directory from package.json productName.
  const shared = {
    ...withGuid,
    appNamePascal: current.artifactNamePascal,
    token: undefined
  }
  if (current.light) {
    return {
      ...shared,
      displayName: variants.light.display,
      appId: `ai.dragon.${variants.light.kebab}`,
      windowsExecutableName: variants.light.display,
      cliName: 'dragon-light',
      msixAppIdWithOrg: `DragonAI.${variants.light.pascal}`
    }
  }

  const stable = variants['']
  return {
    ...shared,
    displayName: stable.display,
    appId: `ai.dragon.${stable.kebab}`,
    windowsExecutableName: stable.display,
    cliName: 'dragon',
    msixAppIdWithOrg: `DragonAI.${stable.pascal}`
  }
}

/**
 * Windows packages must share one OS identity even when electron-builder is
 * invoked as `--win` on a non-Windows packager. Isolation tests pass the
 * host/argv in as data — they never patch process.platform.
 *
 * @param {readonly string[]} [argv]
 * @param {string} [platform]
 * @returns {string}
 */
function packagingPlatform(argv = process.argv, platform = process.platform) {
  return platform === 'win32' || argv.includes('--win') ? 'win32' : platform
}

const { channelBuildRequest } = require('../../scripts/msix-shared.mjs')
const request = channelBuildRequest()

// A channel created with --branding stable copies stable's identity, so it IS
// the regular app. It must also run like one: a token would make the runtime
// pin a userData dir and single-instance lock that installed stable doesn't use.
// The updater reads the token from the stamped request, not from this export.
const officialChannel =
  request !== null &&
  ['appId', 'displayName', 'appNamePascal', 'artifactNamePascal', 'windowsExecutableName', 'cliName', 'msixAppIdWithOrg'].every(
    key => request.identity[key] === identity[key]
  )

const flavored = !request
  ? identity
  : officialChannel
    ? { ...identity, channel: request.channel }
    : { ...request.identity, store: false, light: false, channel: request.channel, nsisGuid: WINDOWS_NSIS_GUID }

const resolved = finalizeIdentity(flavored, packagingPlatform())

Object.defineProperty(resolved, 'finalizeIdentity', { value: finalizeIdentity })
Object.defineProperty(resolved, 'WINDOWS_NSIS_GUID', { value: WINDOWS_NSIS_GUID })
Object.defineProperty(resolved, 'packagingPlatform', { value: packagingPlatform })
Object.defineProperty(resolved, 'flavorIdentity', { value: Object.freeze({ ...flavored }) })
module.exports = Object.freeze(resolved)
