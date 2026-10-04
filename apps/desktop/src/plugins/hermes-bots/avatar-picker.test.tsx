/**
 * Generate tab empty state: when no image backend is configured, the boxed
 * spot is a link to Capabilities → Tools → Image Generation — not a
 * restart-gateway message.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AvatarPicker } from './avatar-picker'
import { $imagenAvailable, IMAGE_GEN_SETTINGS_PATH } from './avatar-image'
import { translateBotsIn } from './i18n-test-helper'

const { navigate } = vi.hoisted(() => ({ navigate: vi.fn() }))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const sdk = await importOriginal<typeof HermesSdk>()

  return {
    ...sdk,
    host: { ...sdk.host, navigate, request: vi.fn() },
    usePluginI18n: () => translateBotsIn('en')
  }
})

const noop = () => undefined

beforeEach(() => {
  vi.clearAllMocks()
  $imagenAvailable.set(false)
})

describe('Generate tab without an image model', () => {
  it('links to the image model picker instead of asking to restart the gateway', async () => {
    render(<AvatarPicker color={null} image={null} onColor={noop} onImage={noop} onShape={noop} shape="circle" />)

    fireEvent.click(screen.getByRole('button', { name: 'Generate' }))

    const link = await screen.findByRole('button', { name: 'Choose an image model' })

    fireEvent.click(link)
    expect(navigate).toHaveBeenCalledWith(IMAGE_GEN_SETTINGS_PATH)
    expect(screen.queryByText(/Restart gateway/i)).toBeNull()
  })
})
