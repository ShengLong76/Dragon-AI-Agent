// @vitest-environment node
import { describe, expect, it, vi } from 'vitest'

import { isHermesHubClipboardWrite, isHermesHubExternalUrl, isHermesHubOrigin } from './hub-iframe-policy'
import { createWindowOpenHandler, describeDeniedUrl } from './window-open-policy'

describe('hub-iframe-policy predicates', () => {
  it('admits no hub origin — Dragon does not embed the upstream picker', () => {
    expect(isHermesHubOrigin('https://hermes-agent.nousresearch.com')).toBe(false)
    expect(isHermesHubOrigin('https://nousresearch.github.io')).toBe(false)
    expect(isHermesHubOrigin('null')).toBe(false)
    expect(isHermesHubOrigin('')).toBe(false)
    expect(isHermesHubOrigin(null)).toBe(false)
    expect(isHermesHubOrigin(undefined)).toBe(false)
    expect(isHermesHubOrigin('https://evil.example')).toBe(false)
  })

  it('still classifies http/https/mailto as the only external schemes', () => {
    expect(isHermesHubExternalUrl('https://github.com/NousResearch/hermes-agent')).toBe(true)
    expect(isHermesHubExternalUrl('http://example.com/docs')).toBe(true)
    expect(isHermesHubExternalUrl('mailto:support@example.com')).toBe(true)

    expect(isHermesHubExternalUrl('file:///etc/passwd')).toBe(false)
    expect(isHermesHubExternalUrl('javascript:alert(1)')).toBe(false)
    expect(isHermesHubExternalUrl('hermes://internal')).toBe(false)
    expect(isHermesHubExternalUrl('not a url')).toBe(false)
  })

  it('grants clipboard-write to no frame', () => {
    expect(isHermesHubClipboardWrite('https://hermes-agent.nousresearch.com')).toBe(false)
    expect(isHermesHubClipboardWrite('https://nousresearch.github.io')).toBe(false)
    expect(isHermesHubClipboardWrite('null')).toBe(false)
    expect(isHermesHubClipboardWrite(null)).toBe(false)
  })
})

describe('createWindowOpenHandler', () => {
  const baseDetails = { url: 'https://github.com/NousResearch/hermes-agent' }

  it('still denies artifact frames (opaque origin) with NO external open', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => 'null',
      openExternalUrl
    })

    expect(handler(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('does not delegate former hub origins — native hub has no iframe carve-out', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => 'https://hermes-agent.nousresearch.com',
      openExternalUrl
    })

    expect(handler(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('does not delegate the former GitHub Pages hub origin either', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => 'https://nousresearch.github.io',
      openExternalUrl
    })

    expect(handler({ url: 'https://docs.example.com/x' })).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('never delegates file:// or unknown schemes', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => 'https://hermes-agent.nousresearch.com',
      openExternalUrl
    })

    expect(handler({ url: 'file:///C:/x.html' })).toEqual({ action: 'deny' })
    expect(handler({ url: 'javascript:alert(1)' })).toEqual({ action: 'deny' })
    expect(handler({ url: 'not a url' })).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('a throwing opener probe or external open stays deny-only', () => {
    const openExternalUrl = vi.fn(() => {
      throw new Error('boom')
    })

    const throwingProbe = createWindowOpenHandler(undefined, {
      getOpenerOrigin: () => {
        throw new Error('probe failed')
      },
      openExternalUrl
    })

    expect(throwingProbe(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('a throwing logging observer cannot change the decision', () => {
    const openExternalUrl = vi.fn()

    const handler = createWindowOpenHandler(
      () => {
        throw new Error('log failed')
      },
      {
        getOpenerOrigin: () => 'https://hermes-agent.nousresearch.com',
        openExternalUrl
      }
    )

    expect(handler(baseDetails)).toEqual({ action: 'deny' })
    expect(openExternalUrl).not.toHaveBeenCalled()
  })

  it('without trusted options the handler is side-effect-free deny (CVE-2026-70608 posture)', () => {
    const handler = createWindowOpenHandler()

    expect(handler({ url: 'https://anything.example' })).toEqual({ action: 'deny' })
  })
})

describe('describeDeniedUrl', () => {
  it('logs origin only, never the full URL', () => {
    expect(describeDeniedUrl('https://example.com/path?token=secret')).toBe('https://example.com')
    expect(describeDeniedUrl('data:text/html,foo')).toBe('data:')
    expect(describeDeniedUrl('not a url')).toBe('<unparseable>')
  })
})
