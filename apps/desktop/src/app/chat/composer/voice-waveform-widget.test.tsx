import { act, cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { I18nProvider } from '@/i18n'

import { VoiceWaveformWidget } from './voice-waveform-widget'

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

function barHeights(container: HTMLElement): number[] {
  return [...container.querySelectorAll<HTMLElement>('[data-slot="voice-waveform-bars"] span')].map(bar =>
    Number.parseFloat(bar.style.height)
  )
}

function flushWaveformFrame() {
  return act(async () => {
    await new Promise<void>(resolve => {
      window.requestAnimationFrame(() => resolve())
    })
  })
}

describe('VoiceWaveformWidget listening meter', () => {
  it('raises the Listening bars when the live mic level rises', async () => {
    const { container, rerender } = render(
      <I18nProvider configClient={null} initialLocale="en">
        <VoiceWaveformWidget
          level={0}
          muted={false}
          onEnd={() => undefined}
          onToggleMute={() => undefined}
          status="listening"
        />
      </I18nProvider>
    )

    await flushWaveformFrame()
    const quiet = Math.max(...barHeights(container))

    rerender(
      <I18nProvider configClient={null} initialLocale="en">
        <VoiceWaveformWidget
          level={0.8}
          muted={false}
          onEnd={() => undefined}
          onToggleMute={() => undefined}
          status="listening"
        />
      </I18nProvider>
    )

    await flushWaveformFrame()
    const loud = Math.max(...barHeights(container))

    expect(quiet).toBeGreaterThan(0)
    expect(loud).toBeGreaterThan(quiet)
  })
})
