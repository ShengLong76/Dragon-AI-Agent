// data-paths.ts — typed re-export of the shared pure resolver in data-paths.mjs.
// The app imports these names here (extensionless, for the tsc/esbuild build);
// the CI smoke driver imports the .mjs directly because Node's type-stripping
// cannot resolve extensionless TypeScript imports.
export {
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
} from './data-paths.mjs'
export type { HermesHomeOptions } from './data-paths.mjs'
