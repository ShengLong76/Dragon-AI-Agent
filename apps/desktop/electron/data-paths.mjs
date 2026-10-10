// data-paths.mjs — the pure path-resolution core, shared by the desktop app
// (via data-paths.ts, a typed re-export) and the CI smoke driver (which runs
// under Node's type-stripping and therefore cannot import the app's
// extensionless TypeScript directly). No Electron imports here; only node:path.
//
// data-paths.ts re-exports these names and adds the TypeScript-facing
// `HermesHomeOptions` interface. Keep the two in lockstep: every behavior in
// this file is exercised by data-paths.test.ts through the re-export.

import path from 'node:path'

/** Current Windows LocalAppData product folder (no Claude). */
export const WINDOWS_PRODUCT_DIR = 'DragonAI'
/** Leftover v0.2 and earlier Windows product folder. */
export const WINDOWS_LEGACY_PRODUCT_DIR = 'DragonAIClaude'
/** Current POSIX hidden home directory (no Claude). */
export const POSIX_PRODUCT_DIR = '.dragon-ai'
/** Leftover POSIX home directory from the Claude-branded rebrand. */
export const POSIX_LEGACY_PRODUCT_DIR = '.dragon-ai-claude'

const PRODUCT_STATE_MARKERS = ['config.yaml', '.env', 'sessions', 'memories', 'state.db']

/** A HERMES_HOME rooted inside a `profiles/` directory names the profile's
 * parent (the home), not the profile directory itself. */
function normalizeHermesHomeRoot(hermesHome, pathModule) {
  if (!hermesHome) {
    return hermesHome
  }
  const resolved = pathModule.resolve(String(hermesHome))
  const parent = pathModule.dirname(resolved)
  if (pathModule.basename(parent).toLowerCase() === 'profiles') {
    return pathModule.dirname(parent)
  }
  return resolved
}

function pathModuleFor(platform) {
  return platform === 'win32' ? path.win32 : path.posix
}

function sameResolvedPath(left, right, pathModule, platform) {
  const a = pathModule.resolve(left)
  const b = pathModule.resolve(right)
  return platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b
}

export function platformDefaultHermesHome(home, env = process.env, platform = process.platform) {
  const suffix = env.HERMES_DATA_DIR_SUFFIX || ''
  if (platform === 'win32') {
    const base = (env.LOCALAPPDATA || '').trim() || path.win32.join(home, 'AppData', 'Local')
    return path.win32.join(base, WINDOWS_PRODUCT_DIR, 'home') + suffix
  }
  return path.posix.join(home, POSIX_PRODUCT_DIR) + suffix
}

export function platformLegacyHermesHomes(home, env = process.env, platform = process.platform) {
  const suffix = env.HERMES_DATA_DIR_SUFFIX || ''
  if (platform === 'win32') {
    const base = (env.LOCALAPPDATA || '').trim() || path.win32.join(home, 'AppData', 'Local')
    return [path.win32.join(base, WINDOWS_LEGACY_PRODUCT_DIR, 'home') + suffix]
  }
  return [path.posix.join(home, POSIX_LEGACY_PRODUCT_DIR) + suffix]
}

export function homeLooksPopulated(dir, { directoryExists = () => false, fileExists = () => false, pathModule = path } = {}) {
  if (!dir || !directoryExists(dir)) {
    return false
  }
  return PRODUCT_STATE_MARKERS.some(name => {
    const candidate = pathModule.join(dir, name)
    return fileExists(candidate) || directoryExists(candidate)
  })
}

/**
 * One-shot move of a leftover Claude-branded home into the current product
 * home. Prefer rename (same volume). Fall back to a copy that leaves the
 * source in place. Never overwrite a dest that already has product state.
 *
 * @returns {{ migrated: boolean, method?: 'rename' | 'copy', reason?: string, source?: string, dest?: string }}
 */
export function migrateLegacyProductHome({
  dest,
  sources = [],
  platform = 'linux',
  pathModule = pathModuleFor(platform),
  directoryExists = () => false,
  fileExists = () => false,
  renameDirectory,
  copyDirectory,
  writeText,
  mkdirp
} = {}) {
  const populated = dir => homeLooksPopulated(dir, { directoryExists, fileExists, pathModule })
  if (!dest || populated(dest)) {
    return { migrated: false, reason: 'dest-populated' }
  }
  const source = sources.find(
    dir => dir && !sameResolvedPath(dir, dest, pathModule, platform) && populated(dir)
  )
  if (!source) {
    return { migrated: false, reason: 'no-legacy-home' }
  }
  if (!directoryExists(dest) && renameDirectory) {
    try {
      if (mkdirp) {
        mkdirp(pathModule.dirname(dest))
      }
      renameDirectory(source, dest)
      if (writeText) {
        writeText(
          pathModule.join(pathModule.dirname(source), 'MOVED_TO.txt'),
          `This Dragon AI home was moved to:\n${dest}\n`
        )
      }
      return { migrated: true, method: 'rename', source, dest }
    } catch {
      // Same-volume rename can fail (dest parent missing mid-flight, in-use
      // files). Copy is the documented fallback and leaves the source intact.
    }
  }
  if (copyDirectory) {
    if (mkdirp) {
      mkdirp(dest)
    }
    copyDirectory(source, dest)
    if (writeText) {
      writeText(pathModule.join(dest, '.migrated-from-dragon-ai-claude'), `${source}\n`)
    }
    return { migrated: true, method: 'copy', source, dest }
  }
  return { migrated: false, reason: 'no-fs-ops' }
}

export function resolveDesktopUserData(defaultPath, env = process.env) {
  return env.HERMES_DESKTOP_USER_DATA_DIR
    ? path.resolve(env.HERMES_DESKTOP_USER_DATA_DIR)
    : defaultPath + (env.HERMES_DATA_DIR_SUFFIX || '')
}

export function resolveDesktopHermesHome({
  home,
  env = process.env,
  platform = process.platform,
  directoryExists = () => false,
  fileExists = () => false,
  readWindowsHome = () => null,
  renameDirectory,
  copyDirectory,
  writeText,
  mkdirp
}) {
  const paths = pathModuleFor(platform)
  if (env.HERMES_HOME) {
    return normalizeHermesHomeRoot(env.HERMES_HOME, paths)
  }
  // Fresh-install rehearsals must not touch the real Hermes home.
  if (env.HERMES_DESKTOP_USER_DATA_DIR) {
    return paths.join(paths.resolve(env.HERMES_DESKTOP_USER_DATA_DIR), 'hermes-home')
  }
  if (platform === 'win32' && env.HERMES_HOME === undefined) {
    // Explorer can miss setx changes. An explicit empty value opts out of that fallback.
    const registryHome = readWindowsHome()
    if (registryHome) {
      const resolved = normalizeHermesHomeRoot(registryHome, paths)
      const legacyDefaults = platformLegacyHermesHomes(home, env, platform)
      const pointsAtLegacyDefault = legacyDefaults.some(candidate =>
        sameResolvedPath(resolved, candidate, paths, platform)
      )
      if (!pointsAtLegacyDefault) {
        return resolved
      }
    }
  }
  const defaultHome = platformDefaultHermesHome(home, env, platform)
  // Dragon AI owns its home outright: it never adopts another agent
  // install's data directory. It DOES adopt its own previous
  // Claude-branded folder so a reinstall keeps sessions and config.
  if (renameDirectory || copyDirectory) {
    try {
      migrateLegacyProductHome({
        dest: defaultHome,
        sources: platformLegacyHermesHomes(home, env, platform),
        platform,
        pathModule: paths,
        directoryExists,
        fileExists,
        renameDirectory,
        copyDirectory,
        writeText,
        mkdirp
      })
    } catch {
      // A locked leftover folder must not block first launch. The new dest
      // is still used; the user can move DragonAIClaude\home by hand.
    }
  }
  return defaultHome
}
