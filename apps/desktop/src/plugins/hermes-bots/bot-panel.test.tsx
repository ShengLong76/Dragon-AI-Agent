/**
 * The bot profile pane is Details | Library | Computer | Scheduled Jobs.
 * Computer stays (that is where Take over lives). Scheduled Jobs is the cron
 * list only — no screen thumbnail, live desktop, or Open live card.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { translateBots } from './i18n-test-helper'

const { request } = vi.hoisted(() => ({ request: vi.fn() }))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof HermesSdk>()

  return {
    ...sdk,
    host: { ...sdk.host, request, revealPane: vi.fn() },
    usePluginI18n: () => translateBots
  }
})

vi.mock('./screen-pane', () => ({ BotScreenPane: () => <div>live-desktop</div> }))
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
  request.mockResolvedValue({ jobs: [], scoped: 'research' })
  $lastRoster.set([{ connectionId: 'local', name: 'research' }])
  $botPanel.set({ key: 'research', tab: 'computer' })
})

afterEach(() => {
  cleanup()
  $botPanel.set(null)
})

describe('the bot profile pane keeps Computer and adds Scheduled Jobs', () => {
  it('shows all four tabs, keeps Computer, and lists cron without a screen', async () => {
    renderPanel()

    expect(screen.getByRole('tab', { name: 'Details' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Library' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Computer' })).toBeTruthy()
    expect(screen.getByRole('tab', { name: 'Scheduled Jobs' })).toBeTruthy()
    expect(screen.getByText('live-desktop')).toBeTruthy()

    await act(async () => {
      screen.getByRole('tab', { name: 'Scheduled Jobs' }).click()
    })

    expect(await screen.findByRole('button', { name: 'New cron' })).toBeTruthy()
    expect(await screen.findByText('No scheduled jobs yet')).toBeTruthy()
    expect(screen.queryByText('live-desktop')).toBeNull()
    expect(screen.queryByRole('button', { name: /Open live/i })).toBeNull()
    expect(screen.queryByText('Live · bot in control')).toBeNull()
    expect(screen.getByRole('tab', { name: 'Computer' })).toBeTruthy()

    await act(async () => {
      screen.getByRole('tab', { name: 'Computer' }).click()
    })

    expect(screen.getByText('live-desktop')).toBeTruthy()
  })
})
