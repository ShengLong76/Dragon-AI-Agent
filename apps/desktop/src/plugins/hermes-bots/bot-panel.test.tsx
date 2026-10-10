/**
 * The bot profile pane is Details | Library | Computer | Routines.
 * Computer is the live VM desktop. Routines is the cron list only.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { translateBots } from './i18n-test-helper'

const { notify, notifyError, request, requestProfile } = vi.hoisted(() => ({
  notify: vi.fn(),
  notifyError: vi.fn(),
  request: vi.fn(),
  requestProfile: vi.fn()
}))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof HermesSdk>()

  return {
    ...sdk,
    host: { ...sdk.host, notify, notifyError, request, requestProfile, revealPane: vi.fn() },
    usePluginI18n: () => translateBots
  }
})

vi.mock('./screen-pane', () => ({
  BotScreenPane: () => <div>bot-computer</div>
}))
vi.mock('./skills-hub', () => ({ HubSkillsSection: () => <div>library-skills</div> }))

const { $botPanel, BotPanelPane } = await import('./bot-panel')
const { $lastRoster } = await import('./data')

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})

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
  let soul = '# Researcher persona'
  const respond = async (method: string, params?: { soul?: string }) => {
    if (method === 'profiles.describe') {
      return { soul }
    }

    if (method === 'profiles.configure') {
      soul = params?.soul ?? soul

      return { ok: true, applied: { soul: true } }
    }

    return { jobs: [], scoped: 'research' }
  }

  request.mockImplementation(async (method: string, params?: { soul?: string }) => respond(method, params))
  requestProfile.mockImplementation(async (_route: unknown, method: string, params?: { soul?: string }) =>
    respond(method, params)
  )
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

  it('opens a SOUL.md editor on double-click and saves through profiles.configure', async () => {
    renderPanel()

    await act(async () => {
      screen.getByRole('tab', { name: 'Details' }).click()
    })

    expect(await screen.findByText('# Researcher persona')).toBeTruthy()
    expect(screen.getByText('Double-click to edit')).toBeTruthy()

    await act(async () => {
      fireEvent.doubleClick(document.querySelector('[data-slot="soul-preview"]')!)
    })

    const editor = await screen.findByLabelText('SOUL.md')
    expect(editor).toHaveValue('# Researcher persona')
    expect(document.querySelector('[data-slot="soul-editor"]')).toBeTruthy()

    await act(async () => {
      fireEvent.change(editor, { target: { value: '# Updated persona' } })
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Save' }))
    })

    await waitFor(() => {
      expect(request).toHaveBeenCalledWith(
        'profiles.configure',
        expect.objectContaining({
          name: 'research',
          soul: '# Updated persona'
        })
      )
    })
    expect(await screen.findByText('# Updated persona')).toBeTruthy()
    expect(document.querySelector('[data-slot="soul-editor"]')).toBeNull()
    expect(notifyError).not.toHaveBeenCalled()
  })

  it('toasts when saving SOUL.md fails', async () => {
    request.mockImplementation(async (method: string) => {
      if (method === 'profiles.describe') {
        return { soul: '# Researcher persona' }
      }

      if (method === 'profiles.configure') {
        throw new Error('disk full')
      }

      return { jobs: [], scoped: 'research' }
    })

    renderPanel()

    await act(async () => {
      screen.getByRole('tab', { name: 'Details' }).click()
    })
    await screen.findByText('# Researcher persona')

    await act(async () => {
      fireEvent.doubleClick(document.querySelector('[data-slot="soul-preview"]')!)
    })
    await act(async () => {
      fireEvent.click(await screen.findByRole('button', { name: 'Save' }))
    })

    await waitFor(() => {
      expect(notifyError).toHaveBeenCalled()
    })
    expect(notifyError.mock.calls[0][1]).toBe('Could not save SOUL.md')
    expect(document.querySelector('[data-slot="soul-editor"]')).toBeTruthy()
  })
})
