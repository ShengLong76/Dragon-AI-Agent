import { describe, expect, it } from 'vitest'

import {
  DRAGON_FEATURED_SKILLS,
  HYPERFRAMES_HUB_SKILL,
  HYPERFRAMES_IDENTIFIER,
  hubSkillKey,
  isHyperFramesIdentifier,
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
      {
        aliases: undefined,
        description: 'local',
        identifier: 'web-research',
        name: 'web-research',
        source: undefined
      }
    ])
  })
})

describe('HyperFrames featured catalog entry', () => {
  it('lists HyperFrames as a standalone one-click hub skill with Apache-2.0 credit', () => {
    expect(DRAGON_FEATURED_SKILLS[0]).toEqual(HYPERFRAMES_HUB_SKILL)
    expect(HYPERFRAMES_HUB_SKILL.identifier).toBe(HYPERFRAMES_IDENTIFIER)
    expect(HYPERFRAMES_HUB_SKILL.name).toBe('HyperFrames — make videos from HTML')
    expect(HYPERFRAMES_HUB_SKILL.description).toMatch(/Standalone skill/)
    expect(HYPERFRAMES_HUB_SKILL.description).toMatch(/any bot/)
    expect(HYPERFRAMES_HUB_SKILL.description).toMatch(/Apache-2\.0/)
    expect(HYPERFRAMES_HUB_SKILL.description).toMatch(/heygen-com\/hyperframes/)
    expect(HYPERFRAMES_HUB_SKILL.description).not.toMatch(/hermes/i)
    expect(isHyperFramesIdentifier(HYPERFRAMES_IDENTIFIER)).toBe(true)
    expect(isHyperFramesIdentifier('heygen-com/hyperframes/skills/hyperframes')).toBe(false)
  })

  it('treats the router skill name as already-installed for the featured card', () => {
    expect(matchesInstalled(HYPERFRAMES_HUB_SKILL, new Set(['hyperframes']))).toBe(true)
    expect(matchesInstalled(HYPERFRAMES_HUB_SKILL, new Set([HYPERFRAMES_IDENTIFIER]))).toBe(true)
    expect(matchesInstalled(HYPERFRAMES_HUB_SKILL, new Set(['other']))).toBe(false)
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
