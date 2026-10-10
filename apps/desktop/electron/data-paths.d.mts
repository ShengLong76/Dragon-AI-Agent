export const WINDOWS_PRODUCT_DIR: 'DragonAI'
export const WINDOWS_LEGACY_PRODUCT_DIR: 'DragonAIClaude'
export const POSIX_PRODUCT_DIR: '.dragon-ai'
export const POSIX_LEGACY_PRODUCT_DIR: '.dragon-ai-claude'

export function platformDefaultHermesHome(
  home: string,
  env?: NodeJS.ProcessEnv,
  platform?: NodeJS.Platform,
): string

export function platformLegacyHermesHomes(
  home: string,
  env?: NodeJS.ProcessEnv,
  platform?: NodeJS.Platform,
): string[]

export function resolveDesktopUserData(defaultPath: string, env?: NodeJS.ProcessEnv): string

export function homeLooksPopulated(
  dir: string,
  options?: {
    directoryExists?: (directory: string) => boolean
    fileExists?: (filePath: string) => boolean
    pathModule?: Pick<typeof import('node:path'), 'join'>
  },
): boolean

export interface LegacyHomeMigration {
  dest: string
  sources?: string[]
  platform?: NodeJS.Platform
  pathModule?: typeof import('node:path').win32 | typeof import('node:path').posix
  directoryExists?: (directory: string) => boolean
  fileExists?: (filePath: string) => boolean
  renameDirectory?: (from: string, to: string) => void
  copyDirectory?: (from: string, to: string) => void
  writeText?: (filePath: string, text: string) => void
  mkdirp?: (directory: string) => void
}

export function migrateLegacyProductHome(options?: LegacyHomeMigration): {
  migrated: boolean
  method?: 'rename' | 'copy'
  reason?: string
  source?: string
  dest?: string
}

export interface HermesHomeOptions {
  home: string
  env?: NodeJS.ProcessEnv
  platform?: NodeJS.Platform
  directoryExists?: (directory: string) => boolean
  fileExists?: (filePath: string) => boolean
  readWindowsHome?: () => string | null
  renameDirectory?: (from: string, to: string) => void
  copyDirectory?: (from: string, to: string) => void
  writeText?: (filePath: string, text: string) => void
  mkdirp?: (directory: string) => void
}

export function resolveDesktopHermesHome(options: HermesHomeOptions): string
