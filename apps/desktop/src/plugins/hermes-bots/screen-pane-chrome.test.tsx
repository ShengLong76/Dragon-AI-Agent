/**
 * Live Computer chrome: no display/geometry, no sandbox sentence, no
 * "Bot is in control". Take over stays, and Open in a larger window sits
 * next to it below the live view.
 */

import { act, render, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'

import type { DisplayStatus } from './screen-connection'
import type * as ScreenConnection from './screen-connection'
import type { RosterRow } from './types'

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof import('@hermes/plugin-sdk')>()
  const { useStore } = await import('@nanostores/react')
  const { onGatewayEvent } = await import('../../contrib/events')

  return {
    ...sdk,
    Button: ({ children, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
      <button {...props}>{children}</button>
    ),
    Codicon: () => null,
    GlyphSpinner: () => null,
    Tip: ({ children }: { children: ReactNode }) => <>{children}</>,
    EmptyState: () => null,
    useValue: useStore,
    host: { ...sdk.host, onEvent: onGatewayEvent }
  }
})
vi.mock('./data', () => ({ botSelectionKey: (bot: RosterRow) => bot.name }))
vi.mock('./i18n', () => ({
  useBots: () => ({
    screen: {
      title: 'Screen',
      youControl: 'You control',
      otherControls: 'Other controls',
      agentControls: 'Bot is in control',
      placementSandbox: (backend: string) => `Screen runs inside the ${backend} sandbox, with the terminal`,
      handBack: 'Hand back',
      takeOver: 'Take over',
      openLarger: 'Open in a larger window',
      reconnect: 'Reconnect',
      streamLost: 'Stream lost'
    }
  })
}))
vi.mock('./screen-connection', async importActual => ({
  ...(await importActual<typeof ScreenConnection>()),
  displayRequest: vi.fn(),
  resolveScreenWsUrl: vi.fn(async () => 'ws://localhost/api/display/ws'),
  isEventForBotScreen: () => true
}))
vi.mock('@novnc/novnc', () => ({
  default: class {
    addEventListener() {}
    disconnect() {}
    focus() {}
  }
}))

import { displayRequest } from './screen-connection'
import { BotScreenPane } from './screen-pane'
import { $screenState } from './screen-state'

const bot: RosterRow = { name: 'default' }

const status = {
  profile: 'default',
  profile_key: '/home/hermes/.hermes',
  supported: true,
  installed: true,
  missing: [],
  running: true,
  pid: 42,
  display: ':20',
  socket: '/tmp/rfb.sock',
  geometry: '1440x900',
  placement: 'terminal:docker',
  install_command: null,
  lease: { holder: 'agent', viewer_id: null, viewer_hash: null, since: 1, reason: '', epoch: 0 }
} as DisplayStatus

beforeEach(() => {
  $screenState.set({})
  vi.mocked(displayRequest)
    .mockReset()
    .mockImplementation(async (_bot, method) =>
      method === 'display.observe' ? { ...status, ticket: 'test-ticket', viewer_id: 'v1' } : status
    )
  vi.stubGlobal(
    'WebSocket',
    class {
      binaryType = ''
      close() {}
    }
  )
})

afterEach(() => vi.unstubAllGlobals())

it('keeps Take over and Open in a larger window below the live view and drops the status texts', async () => {
  const view = render(<BotScreenPane bot={bot} />)
  await waitFor(() => expect(vi.mocked(displayRequest)).toHaveBeenCalledWith(bot, 'display.observe', expect.anything()))
  await act(async () => {})

  expect(view.queryByText(':20')).toBeNull()
  expect(view.queryByText(/1440x900/)).toBeNull()
  expect(view.queryByText(/sandbox, with the terminal/i)).toBeNull()
  expect(view.queryByText('Bot is in control')).toBeNull()

  const canvas = view.container.querySelector('[data-remote-screen]')
  const takeOver = view.getByRole('button', { name: 'Take over' })
  const larger = view.getByRole('button', { name: 'Open in a larger window' })

  expect(canvas).toBeTruthy()
  expect(takeOver).toBeTruthy()
  expect(larger).toBeTruthy()
  expect(canvas!.compareDocumentPosition(takeOver) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  expect(canvas!.compareDocumentPosition(larger) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  view.unmount()
})
