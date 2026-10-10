// product-identity.cjs is the single derivation of the desktop product
// identity; electron/product-identity.ts re-exports it. These tests hold
// the identity contract: the TS accessor resolves to the .cjs object, and
// the two variants disagree on every OS-visible marker (side-by-side
// installs must not collide).
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import { createRequire } from 'node:module'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import type { AppInfo as BuilderAppInfo, Configuration, Metadata, Packager, Protocol } from 'app-builder-lib'
import { build, type BuildResult } from 'esbuild'
import { afterEach, beforeEach, test, vi } from 'vitest'

import type { applyDesktopIdentity, ProductIdentity } from './product-identity'

type PackagingConfiguration = Omit<Configuration, 'extraMetadata' | 'mac' | 'msix' | 'nsis' | 'protocols' | 'win'> & {
  extraMetadata: Metadata
  mac: Omit<NonNullable<Configuration['mac']>, 'extendInfo'> & { extendInfo: { CFBundleExecutable: string } }
  msix: NonNullable<Configuration['msix']>
  nsis: NonNullable<Configuration['nsis']> & { guid: string }
  protocols: Protocol[]
  win: NonNullable<Configuration['win']>
}

const require: NodeJS.Require = createRequire(import.meta.url)

beforeEach((): void => {
  vi.resetModules()
})

afterEach((): void => {
  delete process.env.HERMES_DESKTOP_VARIANT
  delete process.env.HERMES_PAYLOAD_TAG
  delete process.env.HERMES_BUILD_COMMIT
  delete process.env.HERMES_PAYLOAD_VERSION
  vi.resetModules()
})

function loadIdentityModule(): {
  flavorIdentity: ProductIdentity
  finalizeIdentity: (identity: ProductIdentity, platform?: string) => ProductIdentity
  packagingPlatform: (argv?: readonly string[], platform?: string) => string
  WINDOWS_NSIS_GUID: string
} {
  delete require.cache[require.resolve('../product-identity.cjs')]
  return require('../product-identity.cjs')
}

function flavorForVariant(variant: string | undefined): ProductIdentity {
  if (variant === undefined) {
    delete process.env.HERMES_DESKTOP_VARIANT
  } else {
    process.env.HERMES_DESKTOP_VARIANT = variant
  }

  return loadIdentityModule().flavorIdentity
}

async function identityForVariant(variant: string | undefined): Promise<ProductIdentity> {
  flavorForVariant(variant)
  vi.resetModules()

  return (await import('./product-identity')).PRODUCT_IDENTITY
}

test('baked runtime identity never evaluates ambient build selectors', async (): Promise<void> => {
  const dir: string = fs.mkdtempSync(path.join(os.tmpdir(), 'baked-identity-'))

  try {
    const identity: ProductIdentity = await identityForVariant('bundled')

    const result: BuildResult<{ write: false }> = await build({
      stdin: {
        contents: "import {PRODUCT_IDENTITY} from './product-identity'; console.log(JSON.stringify(PRODUCT_IDENTITY))",
        resolveDir: import.meta.dirname
      },
      bundle: true,
      platform: 'node',
      format: 'esm',
      write: false,
      define: { __HERMES_PRODUCT_IDENTITY__: JSON.stringify(identity) }
    })

    const file: string = path.join(dir, 'identity.mjs')
    fs.writeFileSync(file, result.outputFiles[0].text)

    const actual: unknown = JSON.parse(
      execFileSync(process.execPath, [file], {
        encoding: 'utf8',
        env: { ...process.env, HERMES_DESKTOP_VARIANT: 'store', HERMES_BUILD_COMMIT: 'a'.repeat(40) }
      })
    )

    assert.deepEqual(actual, identity)
  } finally {
    fs.rmSync(dir, { recursive: true, force: true })
  }
})

test('nonstable runtime pins userData before the app name can change', async (): Promise<void> => {
  const stable: ProductIdentity = flavorForVariant('bundled')
  process.env.HERMES_PAYLOAD_TAG = 'v0.28.0+canary.20260818T000000Z'
  const canary: ProductIdentity = flavorForVariant('bundled')
  const runtime: { applyDesktopIdentity: typeof applyDesktopIdentity } = await import('./product-identity')
  const root: string = fs.mkdtempSync(path.join(os.tmpdir(), 'identity-userdata-'))
  const paths: Record<string, string> = { appData: root, userData: path.join(root, 'Hermes') }
  let name: string = 'Hermes'

  const app: Parameters<typeof applyDesktopIdentity>[0] = {
    getPath: (key: string): string => paths[key],
    setPath: (key: string, value: string): void => {
      assert.ok(fs.statSync(value).isDirectory())
      paths[key] = value
    },
    setName: (value: string): void => {
      name = value
    }
  }

  try {
    assert.equal(runtime.applyDesktopIdentity(app, stable), null)
    assert.equal(paths.userData, path.join(root, 'Hermes'))
    assert.equal(runtime.applyDesktopIdentity(app, canary), canary.displayName)
    assert.equal(paths.userData, path.join(paths.appData, canary.appNamePascal))
    assert.equal(name, canary.displayName)
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})

test.each([
  [undefined, 'Dragon AI', 'dragon', 'latest', 'canary'],
  ['bundled', 'Dragon AI Agent', 'dragon', 'latest', 'canary'],
  ['light', 'Dragon AI Light', 'dragon-light', 'light', 'light-canary']
] as const)(
  '%s separates stable, canary and independent commits',
  async (
    variant: string | undefined,
    display: string,
    cli: string,
    channel: string,
    canaryChannel: string
  ): Promise<void> => {
    const stable: ProductIdentity = flavorForVariant(variant)
    assert.equal(stable.displayName, display)
    assert.equal(stable.channel, channel)
    assert.equal(stable.light, variant === 'light')
    assert.equal(stable.storeMsix, undefined)
    const identities: ProductIdentity[] = [stable]

    for (const [tag, commit, expectedCli, expectedChannel] of [
      ['v1.2.3+canary.20260818T000000Z', '', `${cli}-canary`, canaryChannel],
      ['', 'abcdef1234567890abcdef1234567890abcdef12', `${cli}-abcdef1`, null],
      ['', '1234567890abcdef1234567890abcdef12345678', `${cli}-1234567`, null]
    ] as const) {
      process.env.HERMES_PAYLOAD_TAG = tag
      process.env.HERMES_BUILD_COMMIT = commit
      const current: ProductIdentity = flavorForVariant(variant)
      assert.equal(current.channel, expectedChannel)
      assert.equal(current.cliName, expectedCli)
      assert.equal(current.windowsExecutableName, expectedCli)
      assert.equal(current.artifactNamePascal, stable.artifactNamePascal)
      assert.deepEqual(current, flavorForVariant(variant))

      if (commit) {
        assert.equal(current.displayName, `${display} ${commit.slice(0, 7)}`)
      }

      for (const previous of identities) {
        for (const field of [
          'displayName',
          'appId',
          'appNamePascal',
          'msixAppIdWithOrg',
          'windowsExecutableName',
          'cliName'
        ] as const) {
          assert.notEqual(current[field], previous[field], `${field} must isolate installations`)

          if (commit) {
            assert.ok(current[field].includes(commit.slice(0, 7)))
          }
        }
      }

      identities.push(current)
    }

    process.env.HERMES_BUILD_COMMIT = 'not-a-sha'
    process.env.HERMES_PAYLOAD_TAG = 'v1.2.3'
    assert.deepEqual(flavorForVariant(variant), stable)
  }
)

test('light and bundled retain distinct OS markers from the full client', async (): Promise<void> => {
  const full: ProductIdentity = flavorForVariant(undefined)

  for (const variant of ['bundled', 'light']) {
    const other: ProductIdentity = flavorForVariant(variant)

    for (const field of ['displayName', 'appId', 'appNamePascal'] as const) {
      assert.notEqual(other[field], full[field])
    }

    if (variant === 'light') {
      assert.notEqual(other.msixAppIdWithOrg, full.msixAppIdWithOrg)
      assert.notEqual(other.channel, full.channel)
    }
  }
})

test('packaging isolates boot metadata and executable names without renaming release artifacts', async (): Promise<void> => {
  const pkg: { name: string; productName: string; version: string; description: string } = require('../package.json')

  const load: () => PackagingConfiguration = (): PackagingConfiguration => {
    delete require.cache[require.resolve('../electron-builder.config.cjs')]

    return require('../electron-builder.config.cjs')
  }

  const { finalizeIdentity, packagingPlatform } = loadIdentityModule()
  const stableIdentity: ProductIdentity = flavorForVariant('bundled')
  const stable: PackagingConfiguration = load()
  assert.equal(stable.extraMetadata.productName || pkg.productName, pkg.productName)

  process.env.HERMES_PAYLOAD_TAG = 'v0.28.0'
  process.env.HERMES_BUILD_COMMIT = ''
  assert.equal(load().msix.customManifestPath, 'build/msix-manifest.xml')

  for (const build of ['canary', 'abcdef1234567890abcdef1234567890abcdef12']) {
    process.env.HERMES_PAYLOAD_TAG = build === 'canary' ? 'v0.28.0+canary.20260818T000000Z' : ''
    process.env.HERMES_BUILD_COMMIT = build === 'canary' ? '' : build
    const flavor: ProductIdentity = flavorForVariant('bundled')
    const identity: ProductIdentity = finalizeIdentity(flavor, packagingPlatform())
    const windows: ProductIdentity = finalizeIdentity(flavor, 'win32')
    const config: PackagingConfiguration = load()
    // Electron bootstrap gives productName precedence over name. appId alone
    // changes neither its early userData lookup nor its single-instance lock.
    // Windows (and `electron-builder --win`) collapse flavor into the shared
    // Dragon AI install, so extraMetadata.productName stays the package default.
    if (identity.appNamePascal !== identity.artifactNamePascal) {
      assert.equal(config.extraMetadata.productName, identity.displayName)
      assert.notEqual(config.extraMetadata.name, stableIdentity.appNamePascal)
    } else {
      assert.equal(config.extraMetadata.productName, undefined)
    }
    assert.equal(config.extraMetadata.name, identity.appNamePascal)
    assert.equal(config.win.executableName, windows.windowsExecutableName)
    assert.equal(config.nsis.guid, windows.nsisGuid)
    assert.equal(config.nsis.shortcutName, windows.displayName)
    assert.equal(config.nsis.uninstallDisplayName, windows.displayName)

    const {
      AppInfo
    }: { AppInfo: typeof BuilderAppInfo } = require('../../../node_modules/app-builder-lib/dist/appInfo.js')

    const appInfo: BuilderAppInfo = new AppInfo(
      { config, metadata: { ...pkg, ...config.extraMetadata } } as Packager,
      null,
      config.win
    )

    // Windows packaging, afterPack, rollback preservation and final signing
    // all consume this resolved name, not the display name.
    assert.equal(appInfo.productFilename, windows.windowsExecutableName)
    assert.equal(config.mac.extendInfo.CFBundleExecutable, config.executableName)
    assert.equal(config.artifactName, stable.artifactName)
    assert.equal(config.msix.customManifestPath, 'build/msix-manifest.xml')

    const {
      appIdentity
    }: {
      appIdentity: (desktopDir: string) => { name: string; identity: ProductIdentity }
    } = require('../../../scripts/msix-shared.mjs')

    process.env.HERMES_PAYLOAD_VERSION = '0.28.0'
    const artifact: ReturnType<typeof appIdentity> = appIdentity(fileURLToPath(new URL('../', import.meta.url)))
    assert.equal(artifact.name, identity.artifactNamePascal)
    assert.equal(artifact.identity.msixAppIdWithOrg, config.msix.identityName)
    assert.deepEqual(config.protocols[0].schemes, ['hermes'])

    if (build !== 'canary') {
      assert.equal(config.publish, null)
      assert.equal(config.mac.publish, null)
    }
  }
})

test('store inherits the bundled app identity (shared userData) but swaps the MSIX packaging identity', async (): Promise<void> => {
  const bundled: ProductIdentity = await identityForVariant('bundled')
  const store: ProductIdentity = await identityForVariant('store')

  // Same Electron app: displayName/appNamePascal (-> shared userData dir),
  // appId, and the out-of-store org-prefixed name are all inherited.
  assert.equal(store.store, true)
  assert.equal(store.light, false)
  assert.equal(store.displayName, bundled.displayName)
  assert.equal(store.appNamePascal, bundled.appNamePascal)
  assert.equal(store.appId, bundled.appId)
  assert.equal(store.msixAppIdWithOrg, bundled.msixAppIdWithOrg)
  // The store build never publishes to a feed.
  assert.equal(store.channel, null)
})

test('nonstable builds cannot claim the official Store package', async (): Promise<void> => {
  process.env.HERMES_PAYLOAD_TAG = 'v0.28.0+canary.20260818T000000Z'
  await assert.rejects(identityForVariant('store'), /Store.*stable/)
  delete process.env.HERMES_PAYLOAD_TAG
  process.env.HERMES_BUILD_COMMIT = 'abcdef1234567890abcdef1234567890abcdef12'
  await assert.rejects(identityForVariant('store'), /Store.*stable/)
})

test('Windows commit, canary, bundled and channel builds share the stable Dragon AI install', async (): Promise<void> => {
  const { finalizeIdentity, packagingPlatform, WINDOWS_NSIS_GUID } = loadIdentityModule()

  assert.equal(WINDOWS_NSIS_GUID, 'b3558a90-7aa1-5a89-862f-0f6a264a6466')
  assert.equal(packagingPlatform(['node', 'electron-builder', '--win', 'nsis'], 'linux'), 'win32')
  assert.equal(packagingPlatform(['node', 'electron-builder', '--mac'], 'linux'), 'linux')
  assert.equal(packagingPlatform(['node', 'electron-builder'], 'win32'), 'win32')

  const stable: ProductIdentity = flavorForVariant(undefined)
  const bundled: ProductIdentity = flavorForVariant('bundled')
  process.env.HERMES_PAYLOAD_TAG = 'v0.28.0+canary.20260818T000000Z'
  const canary: ProductIdentity = flavorForVariant('bundled')
  process.env.HERMES_PAYLOAD_TAG = ''
  process.env.HERMES_BUILD_COMMIT = 'abcdef1234567890abcdef1234567890abcdef12'
  const commit: ProductIdentity = flavorForVariant('bundled')

  const load: () => PackagingConfiguration = (): PackagingConfiguration => {
    delete require.cache[require.resolve('../electron-builder.config.cjs')]
    return require('../electron-builder.config.cjs')
  }

  assert.equal(load().nsis.guid, WINDOWS_NSIS_GUID)

  for (const current of [stable, bundled, canary, commit]) {
    const windows: ProductIdentity = finalizeIdentity(current, 'win32')
    assert.equal(windows.displayName, 'Dragon AI')
    assert.equal(windows.appId, 'ai.dragon.dragon-ai-claude')
    assert.equal(windows.windowsExecutableName, 'Dragon AI')
    assert.equal(windows.cliName, 'dragon')
    assert.equal(windows.nsisGuid, WINDOWS_NSIS_GUID)
    assert.equal(windows.appNamePascal, current.artifactNamePascal)
    assert.equal(windows.token, undefined)
    const runtime: { applyDesktopIdentity: typeof applyDesktopIdentity } = await import('./product-identity')
    assert.equal(
      runtime.applyDesktopIdentity(
        {
          getPath: (): string => assert.fail('Windows Dragon AI userData must stay historical'),
          setPath: (): void => assert.fail('Windows Dragon AI userData must stay historical'),
          setName: (): void => assert.fail('Windows Dragon AI name must stay historical')
        },
        windows
      ),
      null
    )
  }

  process.env.HERMES_PAYLOAD_TAG = 'v0.28.0+canary.20260818T000000Z'
  process.env.HERMES_BUILD_COMMIT = ''
  const light: ProductIdentity = finalizeIdentity(flavorForVariant('light'), 'win32')
  assert.equal(light.displayName, 'Dragon AI Light')
  assert.equal(light.appId, 'ai.dragon.dragon-ai-claude-light')
  assert.equal(light.windowsExecutableName, 'Dragon AI Light')
  assert.equal(light.cliName, 'dragon-light')
  assert.equal(light.nsisGuid, WINDOWS_NSIS_GUID)
})

test('store carries the Partner Center MSIX identity and no other variant does', async (): Promise<void> => {
  const store: ProductIdentity = await identityForVariant('store')
  assert.deepEqual(store.storeMsix, {
    identityName: 'DragonAI.DragonAIClaude',
    publisher: 'CN=EE6D86E4-606F-4E38-B940-AD7248C9D519',
    publisherDisplayName: 'Dragon AI'
  })

  for (const v of [undefined, 'bundled', 'light'] as const) {
    assert.equal((await identityForVariant(v)).storeMsix, undefined, `variant ${v} must carry no storeMsix`)
  }
})
