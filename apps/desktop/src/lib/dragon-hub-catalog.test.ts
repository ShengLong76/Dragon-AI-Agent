import { describe, expect, it } from 'vitest'

import {
  DRAGON_FEATURED_SKILLS,
  hubSkillKey,
  matchesInstalled,
  mergeHubCatalogSkills,
  type HubCatalogSkill
} from './dragon-hub-catalog'

describe('mergeHubCatalogSkills', () => {
  it('keeps upstream hermes-named rows and does not rename them', () => {
    const extra: HubCatalogSkill[] = [
      {
        description: 'Inspect the desktop DOM',
        identifier: 'inspecting-hermes-desktop-dom',
        name: 'inspecting-hermes-desktop-dom',
        source: 'official'
      },
      {
        description: 'Use, configure, and extend the agent.',
        identifier: 'hermes-agent',
        name: 'hermes-agent',
        source: 'official'
      }
    ]

    const merged = mergeHubCatalogSkills(DRAGON_FEATURED_SKILLS, extra)
    const names = merged.map(row => row.name)

    expect(names).toContain('dragon-agent')
    expect(names).toContain('inspecting-hermes-desktop-dom')
    expect(names).toContain('hermes-agent')
    expect(merged.find(row => row.identifier === 'hermes-agent')?.name).toBe('hermes-agent')
  })

  it('collapses duplicate identifiers to the first row', () => {
    const featured: HubCatalogSkill[] = [
      { description: 'local', identifier: 'web-research', name: 'web-research' }
    ]
    const extra: HubCatalogSkill[] = [
      { description: 'registry', identifier: 'web-research', name: 'web-research' }
    ]

    expect(mergeHubCatalogSkills(featured, extra)).toEqual([
      { description: 'local', identifier: 'web-research', name: 'web-research', source: undefined }
    ])
  })
})

describe('matchesInstalled / hubSkillKey', () => {
  it('matches on name or identifier without rewriting either', () => {
    const skill: HubCatalogSkill = {
      description: '',
      identifier: 'official/gifs/gif-search',
      name: 'gif-search'
    }

    expect(hubSkillKey(skill)).toBe('official/gifs/gif-search')
    expect(matchesInstalled(skill, new Set(['gif-search']))).toBe(true)
    expect(matchesInstalled(skill, new Set(['official/gifs/gif-search']))).toBe(true)
    expect(matchesInstalled(skill, new Set(['other']))).toBe(false)
  })
})
