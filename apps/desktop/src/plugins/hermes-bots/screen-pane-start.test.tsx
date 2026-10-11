/**
 * Computer pane Start screen: real docker/image errors, not a generic
 * "gateway connection closed", and a later Start still works.
 */

import { act, fireEvent, render, waitFor } from '@testing-library/react'
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
      start: 'Start screen',
      startFailedLeftoverDisplay: 'leftover display — click Start screen again',
      startFailedCheckDocker:
        'Docker may not be running, or the sandbox image is missing. Start Docker Desktop, then click Start screen again.',
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

function mockStatusThenStart(startImpl: (call: number) => Promise<unknown>) {
  let starts = 0
  vi.mocked(host.requestProfile).mockImplementation(async (_route, method) => {
    if (method === 'display.status') {
      return stopped
    }
    if (method === 'display.start') {
      starts += 1
      return startImpl(starts)
    }
    throw new Error(`unexpected ${method}`)
  })
}

it('shows the real sandbox-image error instead of a generic close', async () => {
  const image =
    "Bot Desktop cannot start: sandbox image 'dragon-sandbox:desktop' is not available locally " +
    'and every fallback failed. Fix: `docker pull nousresearch/hermes-sandbox:desktop`'
  mockStatusThenStart(async () => {
    throw new Error(image)
  })
  const view = render(<BotScreenPane bot={bot} />)
  await act(async () => {})

  fireEvent.click(view.getByRole('button', { name: /Start screen/ }))
  await waitFor(() => expect(view.getByText(image)).toBeTruthy())
  expect(view.queryByText(/gateway connection closed/i)).toBeNull()
  expect(view.getByRole('button', { name: /Start screen/ })).toBeEnabled()
  view.unmount()
})

it('shows the real docker-daemon error instead of a generic close', async () => {
  const daemon = 'Docker daemon is not responding. Ensure Docker is running and try again.'
  mockStatusThenStart(async () => {
    throw new Error(daemon)
  })
  const view = render(<BotScreenPane bot={bot} />)
  await act(async () => {})

  fireEvent.click(view.getByRole('button', { name: /Start screen/ }))
  await waitFor(() => expect(view.getByText(daemon)).toBeTruthy())
  expect(view.queryByText(/gateway connection closed/i)).toBeNull()
  view.unmount()
})

it('maps a heartbeat-closed start to docker/image copy and lets Start retry', async () => {
  mockStatusThenStart(async call => {
    if (call === 1) {
      throw new Error('Dragon AI gateway connection closed')
    }
    // A later Start after docker/tag recovery must not be wedged: the card
    // stays on Screen-is-off and the previous red error is cleared.
    return stopped
  })
  const view = render(<BotScreenPane bot={bot} />)
  await act(async () => {})

  fireEvent.click(view.getByRole('button', { name: /Start screen/ }))
  await waitFor(() =>
    expect(view.getByText(/Docker may not be running, or the sandbox image is missing/)).toBeTruthy()
  )
  expect(view.queryByText('Dragon AI gateway connection closed')).toBeNull()

  const start = view.getByRole('button', { name: /Start screen/ })
  expect(start).toBeEnabled()
  fireEvent.click(start)
  await waitFor(() => expect(view.queryByText(/Docker may not be running/)).toBeNull())
  expect(vi.mocked(host.requestProfile).mock.calls.filter(([, method]) => method === 'display.start')).toHaveLength(2)
  expect(view.getByRole('button', { name: /Start screen/ })).toBeEnabled()
  view.unmount()
})
