/**
 * Computer pane never paints a silent black box. Missing VM, missing
 * display.* methods, and in-flight status each get an honest state.
 */

import { act, render } from '@testing-library/react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { DisplayStatus } from './screen-connection'
import type { RosterRow } from './types'

vi.mock('@hermes/plugin-sdk', async () => {
  const { useStore } = await import('@nanostores/react')
  const { onGatewayEvent } = await import('../../contrib/events')

  return {
    Button: (props: ButtonHTMLAttributes<HTMLButtonElement>) => <button {...props} />,
    Codicon: () => null,
    GlyphSpinner: () => <span>spinner</span>,
    Tip: ({ children }: { children: ReactNode }) => <>{children}</>,
    EmptyState: ({ title, description }: { title: string; description: string }) => (
      <div>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    ),
    useValue: useStore,
    host: { onEvent: onGatewayEvent, requestProfile: vi.fn() }
  }
})
vi.mock('./routing', () => {
  const route = { connectionId: 'local', mode: 'local', profile: 'research', targetProfile: 'research' }

  return { botConnectionRoute: () => route, resolveBotConnectionRoute: () => ({ status: 'resolved', route }) }
})
vi.mock('./data', () => ({ botSelectionKey: (bot: RosterRow) => bot.name }))
vi.mock('./i18n', () => ({
  useBots: () => ({
    screen: {
      title: 'Screen',
      unsupportedTitle: 'No Linux guest on this host',
      unsupportedBody: 'Bot screens run in a Linux guest. Install Docker Desktop and retry.',
      unavailableTitle: 'Screen needs a newer Dragon AI',
      unavailableLocalBody: 'This runtime has no Computer service',
      portalUnavailableManaged: 'Screen is not available on this managed release yet',
      checkingTitle: 'Starting computer…',
      checkingBody: "Asking this bot's runtime for its desktop.",
      statusFailedTitle: 'Computer is not available',
      retry: 'Retry',
      stoppedTitle: 'Screen is off',
      stoppedBody: 'Start this bot’s desktop.',
      start: 'Start',
      attaching: 'Connecting…'
    }
  })
}))
vi.mock('./screen-open', () => ({ openBotScreen: vi.fn() }))

import { host } from '@hermes/plugin-sdk'

import { BotScreenPane } from './screen-pane'
import { $screenState } from './screen-state'

const bot: RosterRow = { name: 'research' }

const stopped: DisplayStatus = {
  profile: 'research',
  profile_key: '/tmp/research',
  supported: true,
  installed: true,
  missing: [],
  running: false,
  pid: null,
  display: null,
  socket: null,
  geometry: '1440x900',
  install_command: null,
  lease: { holder: 'agent', viewer_id: null, viewer_hash: null, since: 1, reason: '', epoch: 0 }
}

beforeEach(() => {
  $screenState.set({})
  vi.mocked(host.requestProfile).mockReset()
})

afterEach(() => {
  vi.restoreAllMocks()
})

it('shows a checking status before display.status returns, not a black canvas', async () => {
  vi.mocked(host.requestProfile).mockImplementation(() => new Promise(() => {}))
  const view = render(<BotScreenPane bot={bot} />)

  expect(view.getByText('Starting computer…')).toBeTruthy()
  expect(view.getByText("Asking this bot's runtime for its desktop.")).toBeTruthy()
  expect(view.container.querySelector('[data-computer-status="checking"]')).toBeTruthy()
  expect(view.container.querySelector('[data-remote-screen]')).toBeNull()
  expect(view.container.querySelector('.bg-black')).toBeNull()
  view.unmount()
})

it('names a runtime that has no display.* methods instead of a black box', async () => {
  vi.mocked(host.requestProfile).mockRejectedValue(
    Object.assign(new Error('Method not found: display.status'), { code: -32601 })
  )
  const view = render(<BotScreenPane bot={bot} />)
  await act(async () => {})

  expect(view.getByText('Screen needs a newer Dragon AI')).toBeTruthy()
  expect(view.getByText('This runtime has no Computer service')).toBeTruthy()
  expect(view.container.querySelector('[data-remote-screen]')).toBeNull()
  expect(view.container.querySelector('.bg-black')).toBeNull()
  view.unmount()
})

it('shows the Linux-guest / Docker instruction when the host cannot run a VM', async () => {
  vi.mocked(host.requestProfile).mockResolvedValue({
    ...stopped,
    supported: false,
    installed: false,
    blocker: 'Install Docker Desktop so this bot can start a Linux VM.'
  })
  const view = render(<BotScreenPane bot={bot} />)
  await act(async () => {})

  expect(view.getByText('No Linux guest on this host')).toBeTruthy()
  expect(view.getByText('Install Docker Desktop so this bot can start a Linux VM.')).toBeTruthy()
  expect(view.container.querySelector('[data-remote-screen]')).toBeNull()
  view.unmount()
})

it('shows Start when the desktop is installed but not running', async () => {
  vi.mocked(host.requestProfile).mockResolvedValue(stopped)
  const view = render(<BotScreenPane bot={bot} />)
  await act(async () => {})

  expect(view.getByText('Screen is off')).toBeTruthy()
  expect(view.getByRole('button', { name: /Start/ })).toBeTruthy()
  expect(view.container.querySelector('[data-remote-screen]')).toBeNull()
  view.unmount()
})

it('shows the connection error and Retry when display.status fails for another reason', async () => {
  vi.mocked(host.requestProfile).mockRejectedValue(new Error('gateway offline'))
  const view = render(<BotScreenPane bot={bot} />)
  await act(async () => {})

  expect(view.getByText('Computer is not available')).toBeTruthy()
  expect(view.getByText('gateway offline')).toBeTruthy()
  expect(view.getByRole('button', { name: 'Retry' })).toBeTruthy()
  expect(view.container.querySelector('[data-computer-status="error"]')).toBeTruthy()
  expect(view.container.querySelector('[data-remote-screen]')).toBeNull()
  view.unmount()
})
