import { describe, expect, it } from 'vitest'

import { listPluginCatalog, lookupPluginCatalogEntry, searchPluginCatalog } from './plugin-catalog'

describe('plugin catalog snapshot', () => {
  it('lists bundled entries including hermes-named ones when present', () => {
    const all = listPluginCatalog()

    expect(all.length).toBeGreaterThan(0)
    expect(all.every(entry => entry.name && entry.repo)).toBe(true)

    const hermesNamed = all.filter(entry => /hermes/i.test(entry.name) || /hermes/i.test(entry.title))

    for (const entry of hermesNamed) {
      expect(entry.name).toMatch(/hermes/i)
    }
  })

  it('looks up an upstream hermes-named entry without renaming it', async () => {
    const catalog = [
      {
        category: 'desktop',
        description: 'Media tools',
        name: 'hermes-media-studio',
        repo: 'https://github.com/NousResearch/hermes-media-studio',
        sha: 'a'.repeat(40),
        title: 'Hermes Media Studio',
        tier: 'community'
      }
    ]

    const found = await lookupPluginCatalogEntry('hermes-media-studio', catalog)

    expect(found).toEqual({
      ok: true,
      entry: {
        name: 'hermes-media-studio',
        repo: 'https://github.com/NousResearch/hermes-media-studio',
        sha: 'a'.repeat(40),
        subdir: undefined
      }
    })
    expect(searchPluginCatalog('hermes-media', catalog).map(row => row.name)).toEqual(['hermes-media-studio'])
  })

  it('rejects unknown names without guessing a git path', async () => {
    await expect(lookupPluginCatalogEntry('not-a-real-plugin', [])).resolves.toEqual({
      ok: false,
      error: 'unknown'
    })
  })
})
