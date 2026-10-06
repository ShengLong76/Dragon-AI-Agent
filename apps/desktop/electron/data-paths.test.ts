import assert from 'node:assert/strict'
import os from 'node:os'
import path from 'node:path'

import { afterEach, test, vi } from 'vitest'

import {
  homeLooksPopulated,
  migrateLegacyProductHome,
  platformDefaultHermesHome,
  platformLegacyHermesHomes,
  POSIX_LEGACY_PRODUCT_DIR,
  POSIX_PRODUCT_DIR,
  resolveDesktopHermesHome,
  resolveDesktopUserData,
  WINDOWS_LEGACY_PRODUCT_DIR,
  WINDOWS_PRODUCT_DIR
} from './data-paths'
import { controlSocketPath } from './ssh-connection'

afterEach((): void => {
  vi.unstubAllEnvs()
})

test.skipIf(process.platform === 'win32')('local SSH sockets use the suffixed default root', (): void => {
  vi.stubEnv('HERMES_DATA_DIR_SUFFIX', 'magic-test')
  const socket: string = controlSocketPath('user', 'host', 22)

  assert.equal(path.dirname(socket), path.join(platformDefaultHermesHome(os.homedir()), 'desktop-ssh'))
})

test('product data roots never include Claude in the folder name', (): void => {
  assert.doesNotMatch(WINDOWS_PRODUCT_DIR, /claude/i)
  assert.doesNotMatch(POSIX_PRODUCT_DIR, /claude/i)
  assert.match(WINDOWS_LEGACY_PRODUCT_DIR, /claude/i)
  assert.match(POSIX_LEGACY_PRODUCT_DIR, /claude/i)
})

test('default data roots append the suffix literally on each platform', (): void => {
  for (const platform of ['linux', 'darwin', 'win32'] as const) {
    const paths: typeof path = platform === 'win32' ? path.win32 : path.posix
    const home: string = platform === 'win32' ? 'C:\\Users\\test' : '/home/test'
    const local: string = paths.join(home, 'AppData', 'Local')
    const userData: string = paths.join(home, 'app-data', 'Hermes')
    const base: string =
      platform === 'win32' ? paths.join(local, WINDOWS_PRODUCT_DIR, 'home') : paths.join(home, POSIX_PRODUCT_DIR)

    for (const suffix of ['', '-asdfasdf', 'magic-test', ' spaced ']) {
      const env: NodeJS.ProcessEnv = { LOCALAPPDATA: local, HERMES_DATA_DIR_SUFFIX: suffix }

      assert.equal(platformDefaultHermesHome(home, env, platform), base + suffix)
      assert.equal(resolveDesktopUserData(userData, env), userData + suffix)
      assert.equal(
        resolveDesktopHermesHome({ home, env, platform, directoryExists: (): boolean => false }),
        base + suffix
      )
      assert.deepEqual(platformLegacyHermesHomes(home, env, platform), [
        platform === 'win32'
          ? paths.join(local, WINDOWS_LEGACY_PRODUCT_DIR, 'home') + suffix
          : paths.join(home, POSIX_LEGACY_PRODUCT_DIR) + suffix
      ])
    }
  }
})

test('explicit homes and userData retain precedence, and suffixed Windows homes never use legacy state', (): void => {
  const home: string = '/home/test'

  const env: NodeJS.ProcessEnv = {
    HERMES_DATA_DIR_SUFFIX: 'magic-test',
    HERMES_HOME: '/explicit/home',
    HERMES_DESKTOP_USER_DATA_DIR: '/explicit/electron'
  }

  assert.equal(resolveDesktopUserData('/default/electron', env), path.resolve(env.HERMES_DESKTOP_USER_DATA_DIR!))
  assert.equal(resolveDesktopHermesHome({ home, env, platform: 'linux' }), env.HERMES_HOME)
  delete env.HERMES_HOME
  assert.equal(resolveDesktopHermesHome({ home, env, platform: 'linux' }), '/explicit/electron/hermes-home')

  const windowsHome: string = 'C:\\Users\\test'
  const windowsEnv: NodeJS.ProcessEnv = { HERMES_DATA_DIR_SUFFIX: 'magic-test' }
  const expected: string = path.win32.join(windowsHome, 'AppData', 'Local', WINDOWS_PRODUCT_DIR, 'homemagic-test')

  assert.equal(
    resolveDesktopHermesHome({
      home: windowsHome,
      env: windowsEnv,
      platform: 'win32',
      directoryExists: (): boolean => true
    }),
    expected
  )
  assert.equal(
    resolveDesktopHermesHome({
      home: windowsHome,
      env: windowsEnv,
      platform: 'win32',
      readWindowsHome: (): string => 'C:\\custom'
    }),
    'C:\\custom'
  )
})

test('homeLooksPopulated requires a product marker, not an empty folder', (): void => {
  const existing = new Set(['C:\\legacy', 'C:\\legacy\\config.yaml'])
  const directoryExists = (dir: string): boolean => dir === 'C:\\legacy'
  const fileExists = (filePath: string): boolean => existing.has(filePath)

  assert.equal(homeLooksPopulated('C:\\legacy', { directoryExists, fileExists, pathModule: path.win32 }), true)
  assert.equal(
    homeLooksPopulated('C:\\empty', {
      directoryExists: (dir: string): boolean => dir === 'C:\\empty',
      fileExists: (): boolean => false,
      pathModule: path.win32
    }),
    false
  )
})

test('migrateLegacyProductHome renames a populated Claude home onto the new dest', (): void => {
  const dest = 'C:\\Users\\test\\AppData\\Local\\DragonAI\\home'
  const source = 'C:\\Users\\test\\AppData\\Local\\DragonAIClaude\\home'
  const dirs = new Set([source])
  const files = new Set([path.win32.join(source, 'config.yaml')])
  let renamed: { from: string; to: string } | null = null
  const notes: Record<string, string> = {}

  const result = migrateLegacyProductHome({
    dest,
    sources: [source],
    platform: 'win32',
    directoryExists: (dir: string): boolean => dirs.has(dir),
    fileExists: (filePath: string): boolean => files.has(filePath),
    renameDirectory: (from: string, to: string): void => {
      renamed = { from, to }
      dirs.delete(from)
      dirs.add(to)
    },
    writeText: (filePath: string, text: string): void => {
      notes[filePath] = text
    },
    mkdirp: (dir: string): void => {
      dirs.add(dir)
    }
  })

  assert.deepEqual(result, { migrated: true, method: 'rename', source, dest })
  assert.deepEqual(renamed, { from: source, to: dest })
  assert.match(notes['C:\\Users\\test\\AppData\\Local\\DragonAIClaude\\MOVED_TO.txt'], /DragonAI\\home/)
})

test('migrateLegacyProductHome copies when dest already exists empty and never overwrites a live dest', (): void => {
  const dest = '/home/test/.dragon-ai'
  const source = '/home/test/.dragon-ai-claude'
  const copied: { from: string; to: string }[] = []

  const emptyDest = migrateLegacyProductHome({
    dest,
    sources: [source],
    platform: 'linux',
    directoryExists: (dir: string): boolean => dir === dest || dir === source,
    fileExists: (filePath: string): boolean => filePath === `${source}/config.yaml`,
    copyDirectory: (from: string, to: string): void => {
      copied.push({ from, to })
    },
    writeText: (): void => undefined,
    mkdirp: (): void => undefined
  })
  assert.deepEqual(emptyDest, { migrated: true, method: 'copy', source, dest })
  assert.deepEqual(copied, [{ from: source, to: dest }])

  copied.length = 0
  const liveDest = migrateLegacyProductHome({
    dest,
    sources: [source],
    platform: 'linux',
    directoryExists: (dir: string): boolean => dir === dest || dir === source,
    fileExists: (filePath: string): boolean =>
      filePath === `${dest}/config.yaml` || filePath === `${source}/config.yaml`,
    copyDirectory: (from: string, to: string): void => {
      copied.push({ from, to })
    }
  })
  assert.deepEqual(liveDest, { migrated: false, reason: 'dest-populated' })
  assert.deepEqual(copied, [])
})

test('resolveDesktopHermesHome migrates a leftover Windows Claude home on first launch', (): void => {
  const windowsHome = 'C:\\Users\\test'
  const local = path.win32.join(windowsHome, 'AppData', 'Local')
  const dest = path.win32.join(local, WINDOWS_PRODUCT_DIR, 'home')
  const source = path.win32.join(local, WINDOWS_LEGACY_PRODUCT_DIR, 'home')
  const dirs = new Set([source])
  const files = new Set([path.win32.join(source, 'config.yaml')])
  let renamed: { from: string; to: string } | null = null

  const resolved = resolveDesktopHermesHome({
    home: windowsHome,
    env: { LOCALAPPDATA: local },
    platform: 'win32',
    directoryExists: (dir: string): boolean => dirs.has(dir),
    fileExists: (filePath: string): boolean => files.has(filePath),
    renameDirectory: (from: string, to: string): void => {
      renamed = { from, to }
    },
    mkdirp: (): void => undefined,
    writeText: (): void => undefined
  })

  assert.equal(resolved, dest)
  assert.deepEqual(renamed, { from: source, to: dest })
})

test('a registry value that still names the Claude default is treated as unset so migration can run', (): void => {
  const windowsHome = 'C:\\Users\\test'
  const local = path.win32.join(windowsHome, 'AppData', 'Local')
  const dest = path.win32.join(local, WINDOWS_PRODUCT_DIR, 'home')
  const source = path.win32.join(local, WINDOWS_LEGACY_PRODUCT_DIR, 'home')
  let migrated = false

  const resolved = resolveDesktopHermesHome({
    home: windowsHome,
    env: { LOCALAPPDATA: local },
    platform: 'win32',
    directoryExists: (dir: string): boolean => dir === source,
    fileExists: (filePath: string): boolean => filePath === path.win32.join(source, 'config.yaml'),
    readWindowsHome: (): string => source,
    renameDirectory: (): void => {
      migrated = true
    },
    mkdirp: (): void => undefined,
    writeText: (): void => undefined
  })

  assert.equal(resolved, dest)
  assert.equal(migrated, true)
})

test('a failed migration still returns the Claude-free dest so launch can continue', (): void => {
  const windowsHome = 'C:\\Users\\test'
  const local = path.win32.join(windowsHome, 'AppData', 'Local')
  const dest = path.win32.join(local, WINDOWS_PRODUCT_DIR, 'home')
  const source = path.win32.join(local, WINDOWS_LEGACY_PRODUCT_DIR, 'home')

  const resolved = resolveDesktopHermesHome({
    home: windowsHome,
    env: { LOCALAPPDATA: local },
    platform: 'win32',
    directoryExists: (dir: string): boolean => dir === source,
    fileExists: (filePath: string): boolean => filePath === path.win32.join(source, 'config.yaml'),
    renameDirectory: (): void => {
      throw new Error('in use')
    },
    copyDirectory: (): void => {
      throw new Error('in use')
    }
  })

  assert.equal(resolved, dest)
})
