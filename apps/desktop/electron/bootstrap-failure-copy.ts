/**
 * User-facing copy for a failed first-run install (bootstrap).
 *
 * The install runner reports the manifest stage name that failed (see
 * electron/bootstrap-runner.ts and the stage manifests in scripts/install.ps1 /
 * scripts/install.sh) plus the raw error text. This module turns that into an
 * Error.message the install overlay can show verbatim: a plain lead sentence
 * naming the step in everyday words and what to do next, with the raw error on
 * a trailing "Details:" line.
 *
 * Pure module: no Electron imports, unit-tested next to it.
 */

/** Manifest stage name -> everyday label. Unknown names fall back to humanizeStageName. */
export const BOOTSTRAP_STAGE_LABELS: ReadonlyMap<string, string> = new Map([
  // scripts/install.ps1 manifest
  ['uv', 'Package installer'],
  ['git', 'Git'],
  ['node', 'Node.js'],
  ['system-packages', 'System packages'],
  ['repository', 'Dragon AI source code'],
  ['docker', 'Docker Desktop (bot screens)'],
  ['products', 'App components'],
  ['python', 'Python runtime'],
  ['venv', 'Python environment'],
  ['dependencies', 'Python packages'],
  ['node-deps', 'Browser tool packages'],
  ['desktop', 'Desktop app build'],
  ['platform-sdks', 'Platform tools'],
  ['configure', 'Settings'],
  ['config-templates', 'Settings templates'],
  ['path', 'Dragon AI command'],
  ['gateway', 'Dragon AI service'],
  ['bootstrap-marker', 'Finishing touches'],
  // scripts/install.sh manifest (names that differ from the Windows one)
  ['prerequisites', 'System prerequisites'],
  ['python-deps', 'Python packages'],
  ['config', 'Settings'],
  ['setup', 'Settings'],
  ['complete', 'Finishing touches']
])

/** `system-packages` -> `System packages`. */
export function humanizeStageName(stage: string): string {
  const words = stage.replace(/[-_]+/g, ' ').trim()

  return words ? words.charAt(0).toUpperCase() + words.slice(1) : ''
}

export function bootstrapStageLabel(stage: string | null | undefined): string | null {
  if (!stage) {
    return null
  }

  return BOOTSTRAP_STAGE_LABELS.get(stage) ?? humanizeStageName(stage)
}

const BOOTSTRAP_FAILURE_REMEDY =
  'Common causes: no internet connection, antivirus blocking the installer, or another copy of Dragon AI running. ' +
  'Close other Dragon AI windows and choose Reload and retry; if it fails again, open the logs and send them to support.'

/** Two setup runs touching the same files: a git lock, the installer's own
 * run lock, or the package/update locks the later steps take. */
const CONCURRENT_SETUP_RE =
  /index\.lock|another git process|install is already running|update is (?:already|still) running|\.install\.lock/i

const CONCURRENT_SETUP_REMEDY =
  'Another Dragon AI setup was running at the same time and both tried to change the same files. ' +
  'Wait a minute for it to finish, then choose Reload and retry. You do not need to reinstall.'

/**
 * Build the Error.message for a failed bootstrap. First line is the plain
 * explanation; the raw error follows on its own "Details:" line.
 */
export function describeBootstrapFailure(failedStage: string | null | undefined, rawError: unknown): string {
  const label = bootstrapStageLabel(failedStage)

  const lead = label
    ? `Setting up Dragon AI stopped during the '${label}' step.`
    : 'Setting up Dragon AI stopped before it could finish.'

  // Installer output still carries the upstream product name in places; the
  // UI shows Dragon AI only (paths like hermes-agent are lowercase and kept).
  const details =
    typeof rawError === 'string' && rawError.trim()
      ? rawError.trim().replace(/\bHermes Agent\b/g, 'Dragon AI').replace(/\bHermes\b/g, 'Dragon AI')
      : 'unknown error'

  const remedy = CONCURRENT_SETUP_RE.test(details) ? CONCURRENT_SETUP_REMEDY : BOOTSTRAP_FAILURE_REMEDY

  return `${lead} ${remedy}\nDetails: ${details}`
}

/**
 * Error.message for an installed Hermes with a piece missing (source tree,
 * Python environment). The renderer's install overlay offers the Repair install
 * button ('hermes:bootstrap:repair'), so the copy points there. `whatIsMissing`
 * names the missing part and its path, e.g. "Python environment missing at /x".
 */
export function missingInstallPartMessage(whatIsMissing: string): string {
  return (
    "Part of Dragon AI's installation is missing (it may have been deleted or quarantined by antivirus). " +
    'Choose Repair install below to put it back — your chats and settings are not affected. ' +
    `Details: ${whatIsMissing}`
  )
}
