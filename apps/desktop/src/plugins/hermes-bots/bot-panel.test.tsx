/**
 * The bot profile pane is Details | Library | Computer | Routines.
 * Computer is the live VM desktop. Routines is the cron list only.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { translateBots } from './i18n-test-helper'
import type { RosterRow } from './types'

const { request, requestProfile } = vi.hoisted(() => ({
  request: vi.fn(),
  requestProfile: vi.fn()
}))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof HermesSdk>()

  return {
    ...sdk,
    host: { ...sdk.host, request, requestProfile, revealPane: vi.fn() },
    usePluginI18n: () => translateBots
  }
})

vi.mock('./screen-pane', () => ({
  BotScreenPane: () => <div>bot-computer</div>
}))
vi.mock('./skills-hub', () => ({ HubSkillsSection: () => <div>library-skills</div> }))

const { $botPanel, BotPanelPane } = await import('./bot-panel')
const { $lastRoster } = await import('./data')

function renderPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  return render(
    <QueryClientProvider client={client}>
      <BotPanelPane />
    </QueryClientProvider>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  const respond = async (method: string) =>
    method === 'profiles.describe' ? { soul: '# Researcher persona' } : { jobs: [], scoped: 'research' }

  request.mockImplementation(async (method: string) => respond(method))
  requestProfile.mockImplementation(async (_route: unknown, method: string) => respond(method))
  $lastRoster.set([{ connectionId: 'local', description: 'Looks things up', name: 'research' }])
  $botPanel.set({ key: 'research', tab: 'computer' })
})

afterEach(() => {
  cleanup()
  $botPanel.set(null)
})

describe('the bot profile pane has four tabs and keeps Computer', () => {
  it('shows Details, Library, Computer, and Routines, with cron only on Routines', async () => {
    renderPanel()

    expect(screen.getByRole('tab', { name: 'Details' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Library' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Computer' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Routines' })).toBeTruthy()
    expect(screen.queryByRole('tab', { name: 'Scheduled Jobs' })).toBeNull()
    expect(screen.queryByText('Take over')).toBeNull()
    expect(screen.getByText('bot-computer')).toBeTruthy()

    await act(async () => {
      screen.getByRole('tab', { name: 'Details' }).click()
    })

    expect(screen.queryByRole('button', { name: 'New cron' })).toBeNull()
    expect(screen.queryByText('No scheduled jobs yet')).toBeNull()
    const profile = screen.getByText('Profile')
    const runsOn = screen.getByText('Runs on')
    const description = screen.getByText('Description')
    const soul = await screen.findByText('SOUL.md')
    expect(profile.compareDocumentPosition(runsOn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(runsOn.compareDocumentPosition(description) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(description.compareDocumentPosition(soul) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(await screen.findByText('# Researcher persona')).toBeTruthy()

    await act(async () => {
      screen.getByRole('tab', { name: 'Routines' }).click()
    })

    expect(await screen.findByRole('button', { name: 'New cron' })).toBeTruthy()
    expect(await screen.findByText('No scheduled jobs yet')).toBeTruthy()
    expect(screen.queryByText('bot-computer')).toBeNull()
    expect(screen.getByRole('tab', { name: 'Computer' })).toBeTruthy()

    await act(async () => {
      screen.getByRole('tab', { name: 'Computer' }).click()
    })

    expect(screen.getByText('bot-computer')).toBeTruthy()
  })
})
