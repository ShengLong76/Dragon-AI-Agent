/**
 * Pinned tiles are the only roster surface a pinned bot has, so Edit and
 * Unpin must work here the same way they do on an unpinned list row.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { $botMeta } from './data'
import { translateBotsIn } from './i18n-test-helper'
import { PinnedBotTiles } from './pinned-tiles'
import type { RosterRow } from './types'

const { ensureBotMetadata, notifyError, request } = vi.hoisted(() => ({
  ensureBotMetadata: vi.fn(),
  notifyError: vi.fn(),
  request: vi.fn()
}))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof HermesSdk>()

  return {
    ...sdk,
    host: { ...sdk.host, notifyError, request },
    usePluginI18n: () => translateBotsIn('en')
  }
})

vi.mock('./canonical-chat', () => ({
  ensureBotMetadata,
  notifyBotOpenFailure: vi.fn(),
  openBotCanonicalChat: vi.fn(),
  prepareBotSource: vi.fn(),
  PROFILE_SESSION_LIST_LIMIT: 200
}))

vi.mock('./roster-actions', () => ({ openRosterBot: vi.fn() }))

const noop = () => undefined

beforeEach(() => {
  vi.clearAllMocks()
  $botMeta.set({})
  ensureBotMetadata.mockResolvedValue({})
  request.mockImplementation(async (method: string) =>
    method === 'profiles.list' ? { profiles: [{ name: 'closer' }] } : { applied: { ui_meta: true } }
  )
})

describe('pinned tiles keep the bot menu', () => {
  it('opens Edit on a pinned bot', async () => {
    const onEdit = vi.fn()
    const bot = { name: 'closer' } as RosterRow

    $botMeta.set({ closer: { pinned: true, title: 'Follow-up Closer' } })
    render(
      <PinnedBotTiles bots={[bot]} onDelete={noop} onEdit={onEdit} onGroup={noop} onNewSection={noop} />
    )

    fireEvent.contextMenu(screen.getByRole('button', { name: 'Follow-up Closer' }))
    fireEvent.click(await screen.findByText('Edit…'))

    expect(onEdit).toHaveBeenCalledWith(bot)
  })

  it('unpins a pinned bot', async () => {
    const bot = { name: 'closer' } as RosterRow

    $botMeta.set({ closer: { pinned: true, title: 'Follow-up Closer' } })
    render(
      <PinnedBotTiles bots={[bot]} onDelete={noop} onEdit={noop} onGroup={noop} onNewSection={noop} />
    )

    fireEvent.contextMenu(screen.getByRole('button', { name: 'Follow-up Closer' }))
    fireEvent.click(await screen.findByText('Unpin'))
    await vi.waitFor(() => expect(request.mock.calls.some(([method]) => method === 'profiles.configure')).toBe(true))

    const [, params] = request.mock.calls.find(([method]) => method === 'profiles.configure')!

    expect(params).toMatchObject({ name: 'closer', ui_meta: { 'hermes-bots': { pinned: false } } })
  })

  it('opens Edit and unpins the default bot the same way', async () => {
    const onEdit = vi.fn()
    const bot = { name: 'default' } as RosterRow

    request.mockImplementation(async (method: string) =>
      method === 'profiles.list' ? { profiles: [{ name: 'default' }] } : { applied: { ui_meta: true } }
    )
    render(
      <PinnedBotTiles bots={[bot]} onDelete={noop} onEdit={onEdit} onGroup={noop} onNewSection={noop} />
    )

    fireEvent.contextMenu(screen.getByRole('button', { name: 'Chief of Staff' }))
    fireEvent.click(await screen.findByText('Edit…'))
    expect(onEdit).toHaveBeenCalledWith(bot)

    fireEvent.contextMenu(screen.getByRole('button', { name: 'Chief of Staff' }))
    fireEvent.click(await screen.findByText('Unpin'))
    await vi.waitFor(() => expect(request.mock.calls.some(([method]) => method === 'profiles.configure')).toBe(true))

    const [, params] = request.mock.calls.find(([method]) => method === 'profiles.configure')!

    expect(params).toMatchObject({ name: 'default', ui_meta: { 'hermes-bots': { pinned: false } } })
  })
})
