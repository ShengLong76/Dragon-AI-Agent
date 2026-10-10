// @vitest-environment jsdom
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type * as HermesApi from '@/hermes'
import type * as HubActions from '@/store/hub-actions'

vi.mock('@/hermes', async importOriginal => ({
  ...(await importOriginal<typeof HermesApi>()),
  getSkillHubSources: vi.fn().mockResolvedValue({ featured: [], installed: {}, index_available: true, sources: [] }),
  searchSkillsHub: vi.fn().mockResolvedValue({ results: [], source_counts: {}, timed_out: [], installed: {} })
}))

vi.mock('@/store/hub-actions', async importOriginal => ({
  ...(await importOriginal<typeof HubActions>()),
  installHubSkill: vi.fn().mockResolvedValue(undefined)
}))

const { EmbeddedHubPicker } = await import('./skills/embedded-hub-picker')
const { PluginCatalogBrowser } = await import('./plugins/plugin-catalog-browser')

afterEach(() => {
  cleanup()
})

describe('Dragon hub chrome', () => {
  it('renders a native Skills Hub with Dragon chrome and no upstream iframe', () => {
    render(<EmbeddedHubPicker installedNames={new Set()} profile={null} />)

    expect(screen.getByText('Dragon AI Skills Hub')).toBeTruthy()
    expect(document.querySelector('iframe')).toBeNull()
    expect(screen.queryByText('Hermes Agent')).toBeNull()
    expect(document.body.textContent).not.toContain('hermes-agent.nousresearch.com')
    expect(document.body.textContent).not.toContain('nousresearch.github.io')
    expect(screen.getByText('dragon-agent')).toBeTruthy()
  })

  it('renders a native plugin catalog with Dragon chrome and no upstream iframe', () => {
    render(<PluginCatalogBrowser installedNames={new Set()} profile={null} />)

    expect(screen.getByText('Plugin catalog')).toBeTruthy()
    expect(document.querySelector('iframe')).toBeNull()
    expect(document.body.textContent).not.toContain('hermes-agent.nousresearch.com')
    expect(document.body.textContent).not.toContain('nousresearch.github.io')
  })
})
