// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type * as HermesApi from '@/hermes'
import type * as HubActions from '@/store/hub-actions'

const searchSkillsHub = vi.fn()
const getSkillHubSources = vi.fn()
const installHubSkill = vi.fn().mockResolvedValue(undefined)

vi.mock('@/hermes', async importOriginal => ({
  ...(await importOriginal<typeof HermesApi>()),
  getSkillHubSources: (...args: unknown[]) => getSkillHubSources(...args),
  searchSkillsHub: (...args: unknown[]) => searchSkillsHub(...args)
}))

vi.mock('@/store/hub-actions', async importOriginal => ({
  ...(await importOriginal<typeof HubActions>()),
  installHubSkill: (...args: unknown[]) => installHubSkill(...args)
}))

vi.mock('@/store/notifications', () => ({
  notify: vi.fn(),
  notifyError: vi.fn()
}))

const { EmbeddedHubPicker } = await import('./embedded-hub-picker')

beforeEach(() => {
  getSkillHubSources.mockResolvedValue({ featured: [], installed: {}, index_available: true, sources: [] })
  searchSkillsHub.mockResolvedValue({ results: [], source_counts: {}, timed_out: [], installed: {} })
  installHubSkill.mockClear()
})

afterEach(() => {
  cleanup()
})

describe('EmbeddedHubPicker', () => {
  it('installs an upstream hermes-named skill with the identifier unchanged', async () => {
    searchSkillsHub.mockResolvedValue({
      installed: {},
      results: [
        {
          description: 'Read the live desktop DOM',
          identifier: 'inspecting-hermes-desktop-dom',
          name: 'inspecting-hermes-desktop-dom',
          repo: null,
          source: 'official',
          tags: [],
          trust_level: 'official'
        }
      ],
      source_counts: {},
      timed_out: []
    })

    render(<EmbeddedHubPicker installedNames={new Set()} profile={null} />)

    fireEvent.change(screen.getByLabelText('Search'), { target: { value: 'hermes desktop' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    expect(await screen.findByText('inspecting-hermes-desktop-dom')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: '+ Add to this Agent: inspecting-hermes-desktop-dom' }))

    await waitFor(() =>
      expect(installHubSkill).toHaveBeenCalledWith('inspecting-hermes-desktop-dom', null)
    )
  })

  it('marks an already-installed featured skill without starting another install', () => {
    render(<EmbeddedHubPicker installedNames={new Set(['dragon-agent'])} profile={null} />)

    expect(screen.getByText('dragon-agent')).toBeTruthy()
    expect(screen.getAllByText('Installed').length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: '+ Add to this Agent: dragon-agent' })).toBeNull()
    expect(installHubSkill).not.toHaveBeenCalled()
  })
})
