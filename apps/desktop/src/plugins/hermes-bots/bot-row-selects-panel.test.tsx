/**
 * Single-click selects a roster bot and updates the right pane immediately.
 * Double-click still opens the Computer tab. Switching bots on Computer must
 * paint Checking / Unavailable / Off+Start / Error — never a blank pane.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { $botPanel, BotPanelPane } from './bot-panel'
import { BotRow } from './bot-row'
import { $lastRoster } from './data'
import { translateBotsIn } from './i18n-test-helper'
import { PinnedBotTiles } from './pinned-tiles'
import { $screenState } from './screen-state'
import type { RosterRow } from './types'

const { openRosterBot, request, requestProfile, revealPane } = vi.hoisted(() => ({
  openRosterBot: vi.fn(),
  request: vi.fn(),
  requestProfile: vi.fn(),
  revealPane: vi.fn()
}))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof HermesSdk>()

  return {
    ...sdk,
    host: {
      ...sdk.host,
      onEvent: () => () => undefined,
      request,
      requestProfile,
      revealPane
    },
    usePluginI18n: () => translateBotsIn('en')
  }
})

vi.mock('./roster-actions', () => ({ openRosterBot }))

const alpha: RosterRow = { connectionId: 'local', description: 'First researcher', name: 'alpha' }
const beta: RosterRow = { connectionId: 'local', description: 'Second researcher', name: 'beta' }

const noop = () => undefined

function renderRosterAndPanel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  return render(
    <QueryClientProvider client={client}>
      <BotRow bot={alpha} onDelete={noop} onEdit={noop} onGroup={noop} onNewSection={noop} />
      <BotRow bot={beta} onDelete={noop} onEdit={noop} onGroup={noop} onNewSection={noop} />
      <BotPanelPane />
    </QueryClientProvider>
  )
}

function row(name: string) {
  return document.querySelector(`[data-roster-key="local::${name}"]`) as HTMLElement
}

beforeEach(() => {
  vi.clearAllMocks()
  openRosterBot.mockResolvedValue(true)
  request.mockResolvedValue({})
  requestProfile.mockImplementation(() => new Promise(() => undefined))
  $lastRoster.set([alpha, beta])
  $botPanel.set({ key: 'alpha', tab: 'computer' })
  $screenState.set({})
})

afterEach(() => {
  $botPanel.set(null)
  $screenState.set({})
})

describe('sidebar click updates the right pane', () => {
  it('single-click selects the bot and keeps the current pane tab', () => {
    renderRosterAndPanel()

    fireEvent.click(row('beta'))

    expect($botPanel.get()).toEqual({ key: 'beta', tab: 'computer' })
    expect(openRosterBot).toHaveBeenCalledWith(beta)
    expect(revealPane).toHaveBeenCalled()
    expect(document.querySelector('[data-slot="dragon-bot-panel"]')?.textContent).toContain('Beta')
  })

  it('single-click on a pinned tile updates the same pane', () => {
    render(
      <>
        <PinnedBotTiles bots={[alpha, beta]} onDelete={noop} onEdit={noop} onGroup={noop} onNewSection={noop} />
        <BotPanelPane />
      </>
    )

    fireEvent.click(row('beta'))

    expect($botPanel.get()).toEqual({ key: 'beta', tab: 'computer' })
    expect(openRosterBot).toHaveBeenCalledWith(beta)
  })

  it('double-click opens the Computer tab', () => {
    $botPanel.set({ key: 'alpha', tab: 'details' })
    renderRosterAndPanel()

    fireEvent.click(row('beta'))
    expect($botPanel.get()).toEqual({ key: 'beta', tab: 'details' })

    fireEvent.doubleClick(row('beta'))
    expect($botPanel.get()).toEqual({ key: 'beta', tab: 'computer' })
  })

  it('Computer pane shows Checking after single-click selection, not a blank canvas', () => {
    renderRosterAndPanel()

    expect(screen.getByText('Starting computer…')).toBeTruthy()
    expect(document.querySelector('[data-computer-status="checking"]')).toBeTruthy()

    fireEvent.click(row('beta'))

    expect($botPanel.get()?.key).toBe('beta')
    expect(screen.getByText('Starting computer…')).toBeTruthy()
    expect(document.querySelector('[data-computer-status="checking"]')).toBeTruthy()
    expect(document.querySelector('[data-remote-screen]')).toBeNull()
    expect(document.querySelector('.bg-black')).toBeNull()
  })
})
