/**
 * Local Dragon Skills Hub catalog + merge helpers.
 *
 * Featured rows are Dragon-branded defaults for the native picker. Hub search
 * results from the registry APIs are shown as the registry returned them —
 * including Hermes-ecosystem names — so an upstream skill still installs.
 */

export interface HubCatalogSkill {
  /** Extra installed names that should mark this card Installed. */
  aliases?: readonly string[]
  description: string
  identifier: string
  name: string
  source?: string
}

/** HyperFrames umbrella id — Skills Hub one-click add + team seat install. */
export const HYPERFRAMES_IDENTIFIER = 'heygen-com/hyperframes'

export const HYPERFRAMES_HUB_SKILL: HubCatalogSkill = {
  aliases: ['hyperframes', 'heygen-com/hyperframes'],
  description:
    'Standalone skill — add to any bot on its own. Make videos from HTML. Installs the HyperFrames core skill set (router /hyperframes) into this bot. Separate from the Marketing team pack and Listing Writer. Apache-2.0 — HeyGen, https://github.com/heygen-com/hyperframes. Needs Node 22+, Chrome, and ffmpeg; prefer the bot Linux sandbox.',
  identifier: HYPERFRAMES_IDENTIFIER,
  name: 'HyperFrames — make videos from HTML',
  source: 'github'
}

export function isHyperFramesIdentifier(identifier: string): boolean {
  const key = identifier.trim().toLowerCase().replace(/\/+$/, '')

  return key === HYPERFRAMES_IDENTIFIER || key === 'hyperframes' || key === 'hyperframes/hyperframes'
}

export const DRAGON_FEATURED_SKILLS: readonly HubCatalogSkill[] = [
  HYPERFRAMES_HUB_SKILL,
  {
    description: 'Use, configure, theme, extend, and orchestrate Dragon AI.',
    identifier: 'dragon-agent',
    name: 'dragon-agent',
    source: 'official'
  },
  {
    description: 'Author in-repo SKILL.md files: frontmatter and structure.',
    identifier: 'dragon-agent-skill-authoring',
    name: 'dragon-agent-skill-authoring',
    source: 'official'
  },
  {
    description: 'Read the live Dragon AI desktop DOM/CSS over CDP.',
    identifier: 'inspecting-dragon-desktop-dom',
    name: 'inspecting-dragon-desktop-dom',
    source: 'official'
  }
]

/** Button label the previous hub page used; keep it so install stays obvious. */
export const ADD_TO_AGENT_LABEL = '+ Add to this Agent'

export function hubSkillKey(skill: Pick<HubCatalogSkill, 'identifier' | 'name'>): string {
  return (skill.identifier || skill.name).trim()
}

/**
 * Featured local rows first, then registry hits. Duplicate identifiers collapse
 * to the first row. Names are not rewritten.
 */
export function mergeHubCatalogSkills(
  featured: readonly HubCatalogSkill[],
  extra: readonly HubCatalogSkill[]
): HubCatalogSkill[] {
  const seen = new Set<string>()
  const out: HubCatalogSkill[] = []

  for (const row of [...featured, ...extra]) {
    const key = hubSkillKey(row)

    if (!key || seen.has(key)) {
      continue
    }

    seen.add(key)
    out.push({
      aliases: row.aliases,
      description: row.description || '',
      identifier: row.identifier || row.name,
      name: row.name || row.identifier,
      source: row.source
    })
  }

  return out
}

export function matchesInstalled(skill: HubCatalogSkill, installed: ReadonlySet<string>): boolean {
  const keys = [skill.name, skill.identifier, hubSkillKey(skill), ...(skill.aliases ?? [])]

  return keys.some(key => key.length > 0 && installed.has(key))
}
