/**
 * The bot profile pane is Details | Library | Computer | Routines.
 * Computer is the live VM desktop. Routines is the cron list only —
 * the standalone Scheduled Jobs column is gone.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

import { translateBots } from './i18n-test-helper'
import type { RosterRow } from './types'

// Radix calls these on open; jsdom doesn't implement them.
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
  Element.prototype.hasPointerCapture = vi.fn(() => false)
  Element.prototype.releasePointerCapture = vi.fn()
})

const { notify, notifyError, request, requestProfile, revealPane } = vi.hoisted(() => ({
  notify: vi.fn(),
  notifyError: vi.fn(),
  request: vi.fn(),
  requestProfile: vi.fn(),
  revealPane: vi.fn()
}))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof HermesSdk>()

  return {
    ...sdk,
    host: { ...sdk.host, notify, notifyError, request, requestProfile, revealPane },
    usePluginI18n: () => translateBots
  }
})

vi.mock('./screen-pane', () => ({
  BotScreenPane: () => <div>bot-computer</div>
}))
vi.mock('./skills-hub', () => ({ HubSkillsSection: () => <div>library-skills</div> }))

const { $botPanel, BotPanelPane, openBotRoutines } = await import('./bot-panel')
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

    expect((await screen.findAllByRole('button', { name: 'New cron' })).length).toBeGreaterThanOrEqual(1)
    expect(await screen.findByText('No scheduled jobs yet')).toBeTruthy()
    expect(screen.getByText(/Schedule a prompt to run on a cron expression/)).toBeTruthy()
    expect(screen.queryByText('bot-computer')).toBeNull()
    expect(screen.getByRole('tab', { name: 'Computer' })).toBeTruthy()
    expect(screen.queryByText(/hermes/i)).toBeNull()

    await act(async () => {
      screen.getAllByRole('button', { name: 'New cron' })[0].click()
    })

    expect((await screen.findByRole('dialog')).textContent).toMatch(/research/i)

    await act(async () => {
      screen.getByRole('button', { name: 'Cancel' }).click()
    })

    expect(screen.queryByRole('dialog')).toBeNull()

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

    const editor = (await screen.findByLabelText('SOUL.md')) as HTMLTextAreaElement
    expect(editor.value).toBe('# Researcher persona')
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

  it('toasts and stays open when the write is acknowledged but not applied', async () => {
    request.mockImplementation(async (method: string) => {
      if (method === 'profiles.describe') {
        return { soul: '# Researcher persona' }
      }

      if (method === 'profiles.configure') {
        return { ok: true, applied: { soul: false } }
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
      expect(notify).toHaveBeenCalledWith(expect.objectContaining({ kind: 'error', message: 'Could not save SOUL.md' }))
    })
    expect(notifyError).not.toHaveBeenCalled()
    expect(document.querySelector('[data-slot="soul-editor"]')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Save' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('asks before discarding unsaved SOUL.md edits', async () => {
    renderPanel()

    await act(async () => {
      screen.getByRole('tab', { name: 'Details' }).click()
    })
    await screen.findByText('# Researcher persona')
    await act(async () => {
      fireEvent.doubleClick(document.querySelector('[data-slot="soul-preview"]')!)
    })

    const editor = await screen.findByLabelText('SOUL.md')
    await act(async () => {
      fireEvent.change(editor, { target: { value: '# Unsaved' } })
    })
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    })

    expect(await screen.findByText('Discard unsaved changes?')).toBeTruthy()
    expect(document.querySelector('[data-slot="soul-editor"]')).toBeTruthy()
    expect((editor as HTMLTextAreaElement).value).toBe('# Unsaved')

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Discard' }))
    })

    await waitFor(() => {
      expect(document.querySelector('[data-slot="soul-editor"]')).toBeNull()
    })
    expect(request).not.toHaveBeenCalledWith('profiles.configure', expect.anything())
  })
})

describe('Routines is the cron surface', () => {
  it('lists, opens, and deletes jobs through cron.manage', async () => {
    const job = {
      enabled: true,
      job_id: 'digest-1',
      name: '[bot:research] Morning digest',
      schedule: 'every 1h',
      state: 'scheduled'
    }

    const respond = async (method: string, params?: { action?: string }) => {
      if (method === 'profiles.describe') {
        return { soul: '' }
      }

      if (method === 'cron.manage' && params?.action === 'remove') {
        return { success: true }
      }

      return { jobs: [job], scoped: 'research' }
    }

    request.mockImplementation(async (method: string, params?: { action?: string }) => respond(method, params))
    requestProfile.mockImplementation(async (_route: unknown, method: string, params?: { action?: string }) =>
      respond(method, params)
    )

    renderPanel()

    await act(async () => {
      screen.getByRole('tab', { name: 'Routines' }).click()
    })

    expect(await screen.findByText('Morning digest')).toBeTruthy()
    expect(screen.getByRole('switch')).toBeTruthy()
    expect(screen.getByRole('button', { name: /delete/i })).toBeTruthy()

    await act(async () => {
      screen.getByRole('button', { name: /delete/i }).click()
    })

    const calls = [...request.mock.calls, ...requestProfile.mock.calls]
    expect(
      calls.some(call => {
        const method = typeof call[0] === 'string' ? call[0] : call[1]
        const params = (typeof call[0] === 'string' ? call[1] : call[2]) as { action?: string } | undefined

        return method === 'cron.manage' && params?.action === 'remove'
      })
    ).toBe(true)

    await act(async () => {
      screen.getByText('Morning digest').click()
    })

    expect(await screen.findByRole('dialog')).toBeTruthy()
    expect(screen.getByRole('dialog').textContent).toMatch(/Morning digest/)
  })

  it('openBotRoutines selects the Routines tab instead of a Scheduled Jobs pane', () => {
    const bot = { connectionId: 'local', name: 'research' } as RosterRow

    openBotRoutines(bot)

    expect($botPanel.get()).toEqual({ key: 'research', tab: 'routines' })
    expect(revealPane).toHaveBeenCalledWith('hermes-bots:bot-panel')
    expect(revealPane).not.toHaveBeenCalledWith('hermes-bots:routines')
  })

  it('never paints hermes as the Chief of Staff handle', async () => {
    $lastRoster.set([{ connectionId: 'local', name: 'default' }])
    $botPanel.set({ key: 'default', tab: 'routines' })

    renderPanel()

    expect(await screen.findByText('Chief of Staff')).toBeTruthy()
    expect(screen.queryByText(/@hermes/i)).toBeNull()
    expect(screen.queryByText(/hermes/i)).toBeNull()
    expect((await screen.findAllByRole('button', { name: 'New cron' })).length).toBeGreaterThanOrEqual(1)
  })
})
