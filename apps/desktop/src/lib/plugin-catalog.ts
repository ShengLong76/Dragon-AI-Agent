/**
 * The curated plugin catalog as the Desktop sees it.
 *
 * Browse/search and `hermes://plugin/install?catalog=` deep links resolve
 * against the in-tree `plugin-catalog/` snapshot bundled with this app — the
 * same pins the backend installer uses. Nothing here installs; callers open
 * the Install Plugin dialog, which still requires the user's explicit
 * confirmation.
 *
 * Hermes-ecosystem entry names stay as the catalog authored them. Dragon's
 * chrome around the list is branded separately.
 */

import snapshot from './plugin-catalog.snapshot.json'

export const PLUGIN_CATALOG_NAME_RE = /^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$/

/** The fields an install needs. */
export interface PluginCatalogEntry {
  name: string
  repo: string
  /** Reviewed pin (40-hex) the backend installs at; may be missing on a malformed feed. */
  sha?: string
  /** Sub-directory of a monorepo the plugin lives in; empty when the repo root is the plugin. */
  subdir?: string
}

export interface PluginCatalogBrowseEntry extends PluginCatalogEntry {
  category: string
  description: string
  tier: string
  title: string
}

export type PluginCatalogLookupError = 'invalid_name' | 'unavailable' | 'unknown'

export type PluginCatalogLookup =
  { ok: false; error: PluginCatalogLookupError } | { ok: true; entry: PluginCatalogEntry }

function asBrowse(raw: unknown): null | PluginCatalogBrowseEntry {
  if (!raw || typeof raw !== 'object') {
    return null
  }

  const row = raw as Record<string, unknown>

  if (typeof row.name !== 'string' || typeof row.repo !== 'string' || !row.repo) {
    return null
  }

  return {
    category: typeof row.category === 'string' ? row.category : 'desktop',
    description: typeof row.description === 'string' ? row.description : '',
    name: row.name,
    repo: row.repo,
    sha: typeof row.sha === 'string' && row.sha ? row.sha : undefined,
    subdir: typeof row.subdir === 'string' && row.subdir ? row.subdir : undefined,
    tier: typeof row.tier === 'string' ? row.tier : 'community',
    title: typeof row.title === 'string' ? row.title : ''
  }
}

const LOCAL_CATALOG: PluginCatalogBrowseEntry[] = (Array.isArray(snapshot) ? snapshot : [])
  .map(asBrowse)
  .filter((entry): entry is PluginCatalogBrowseEntry => entry !== null)

export function listPluginCatalog(
  catalog: readonly PluginCatalogBrowseEntry[] = LOCAL_CATALOG
): PluginCatalogBrowseEntry[] {
  return [...catalog]
}

export function searchPluginCatalog(
  query: string,
  catalog: readonly PluginCatalogBrowseEntry[] = LOCAL_CATALOG
): PluginCatalogBrowseEntry[] {
  const needle = query.trim().toLowerCase()

  if (!needle) {
    return listPluginCatalog(catalog)
  }

  return catalog.filter(entry => {
    const haystacks = [entry.name, entry.title, entry.description, entry.repo]

    return haystacks.some(value => value.toLowerCase().includes(needle))
  })
}

function toInstallEntry(entry: PluginCatalogBrowseEntry): PluginCatalogEntry {
  return {
    name: entry.name,
    repo: entry.repo,
    sha: entry.sha,
    subdir: entry.subdir
  }
}

/**
 * Look one name up in the local catalog. Unknown names are a hard `unknown`,
 * never a guess: the deep link must not turn an arbitrary string into a git
 * identifier the dialog would then clone.
 */
export async function lookupPluginCatalogEntry(
  name: string,
  catalog: readonly PluginCatalogBrowseEntry[] = LOCAL_CATALOG
): Promise<PluginCatalogLookup> {
  const trimmed = name.trim()

  if (!PLUGIN_CATALOG_NAME_RE.test(trimmed)) {
    return { ok: false, error: 'invalid_name' }
  }

  const match = catalog.find(entry => entry.name === trimmed)

  return match ? { ok: true, entry: toInstallEntry(match) } : { ok: false, error: 'unknown' }
}
