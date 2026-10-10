/**
 * The Skills Hub picker embeds a local Dragon-branded catalog (never the
 * upstream docs page headed "Hermes Agent"). Cards post
 * `{type:'hermes-skill-pick'}` and the plugin installs via skills.manage.
 *
 * Picks are pinned to OUR frame's contentWindow and the identifier is
 * charset-checked.
 */

import type * as HermesSdk from '@hermes/plugin-sdk'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { translateBots } from './i18n-test-helper'

const mocks = vi.hoisted(() => ({
  notify: vi.fn(),
  notifyError: vi.fn(),
  request: vi.fn(async (_method: string, _params: Record<string, unknown>) => ({})),
  requestProfile: vi.fn(async (_route: unknown, _method: string, _params: Record<string, unknown>) => ({}))
}))

vi.mock('@hermes/plugin-sdk', async importOriginal => {
  const original = await importOriginal<typeof HermesSdk>()

  return {
    ...original,
    usePluginI18n: () => translateBots,
    host: {
      ...original.host,
      notify: mocks.notify,
      notifyError: mocks.notifyError,
      request: mocks.request,
      requestProfile: mocks.requestProfile
    }
  }
})

const { HubSkillsSection } = await import('./skills-hub')

interface PickMessage {
  identifier?: string
  name?: string
  type?: string
}

/** Mount the section with the hub browser open and hand back its frame. */
function openHubBrowser() {
  const { container } = render(<HubSkillsSection />)

  fireEvent.click(screen.getByRole('button', { name: /browse the full hub/i }))

  const frame = container.querySelector('iframe')

  expect(frame).toBeTruthy()

  return frame as HTMLIFrameElement
}

function postPick(data: PickMessage, options: { origin?: string; source?: null | Window }) {
  window.dispatchEvent(
    new MessageEvent('message', {
      data,
      origin: options.origin ?? window.location.origin,
      source: options.source ?? null
    })
  )
}

function installCalls() {
  return mocks.request.mock.calls.filter(([, params]) => params.action === 'install')
}

function routedInstallCalls() {
  return mocks.requestProfile.mock.calls.filter(([, , params]) => params.action === 'install')
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('hub pick messages', () => {
  it('pins a standalone HyperFrames one-click add on every bot', () => {
    render(<HubSkillsSection />)

    expect(screen.getByText('HyperFrames — make videos from HTML')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '+ Add to this Agent: HyperFrames — make videos from HTML' }))
    expect(installCalls()).toEqual([['skills.manage', { action: 'install', query: 'heygen-com/hyperframes' }]])
  })

  it('embeds a Dragon-branded local catalog, not the Hermes docs site', () => {
    const frame = openHubBrowser()
    const page = frame.getAttribute('srcdoc') || ''

    expect(frame.getAttribute('src')).toBeNull()
    expect(page).toContain('Dragon AI')
    expect(page).toContain('dragon-agent')
    expect(page).toContain('HyperFrames — make videos from HTML')
    expect(page).toContain('heygen-com/hyperframes')
    expect(page).toContain('Apache-2.0')
    expect(page).not.toContain('Hermes Agent')
    expect(page).not.toContain('hermes-agent.nousresearch.com')
    expect(page).not.toContain('nousresearch.github.io')
    expect(screen.getByText('Dragon AI Skills Hub')).toBeTruthy()
  })

  it('accepts an install message from the local picker frame', () => {
    const frame = openHubBrowser()

    postPick(
      { identifier: 'dragon-agent', name: 'dragon-agent', type: 'hermes-skill-pick' },
      { source: frame.contentWindow }
    )

    expect(installCalls()).toEqual([['skills.manage', { action: 'install', query: 'dragon-agent' }]])
  })

  it('one-click adds HyperFrames to the chosen bot via the umbrella identifier', () => {
    const frame = openHubBrowser()

    postPick(
      {
        identifier: 'heygen-com/hyperframes',
        name: 'HyperFrames — make videos from HTML',
        type: 'hermes-skill-pick'
      },
      { source: frame.contentWindow }
    )

    expect(installCalls()).toEqual([['skills.manage', { action: 'install', query: 'heygen-com/hyperframes' }]])
  })

  it('pins the hub frame to a script-only sandbox', () => {
    const frame = openHubBrowser()

    expect(frame.getAttribute('sandbox')).toBe('allow-scripts allow-same-origin')
  })

  it('routes an existing source-scoped bot install through its owner connection', async () => {
    const { container } = render(
      <HubSkillsSection
        bot={{
          name: 'worker',
          remoteSource: true,
          route: {
            connectionId: 'remote-a',
            mode: 'remote',
            profile: 'worker',
            targetProfile: 'backend-worker'
          },
          sourceScoped: true
        }}
      />
    )

    fireEvent.click(screen.getByRole('button', { name: /browse the full hub/i }))
    const frame = container.querySelector('iframe') as HTMLIFrameElement

    postPick(
      { identifier: 'dragon-agent', name: 'dragon-agent', type: 'hermes-skill-pick' },
      { source: frame.contentWindow }
    )

    await waitFor(() => expect(routedInstallCalls()).toHaveLength(1))
    expect(routedInstallCalls()).toEqual([
      [
        expect.objectContaining({
          connectionId: 'remote-a',
          mode: 'remote',
          profile: 'worker',
          targetProfile: 'backend-worker'
        }),
        'skills.manage',
        {
          action: 'install',
          profile: 'backend-worker',
          query: 'dragon-agent'
        }
      ]
    ])
    expect(installCalls()).toEqual([])
  })

  it('regression: ignores a same-origin window that is NOT the picker frame', () => {
    openHubBrowser()

    postPick(
      { identifier: 'dragon-agent', name: 'dragon-agent', type: 'hermes-skill-pick' },
      {
        source: window
      }
    )

    expect(installCalls()).toEqual([])
  })

  it('ignores anything posted from another origin', () => {
    const frame = openHubBrowser()

    postPick(
      { identifier: 'dragon-agent', name: 'dragon-agent', type: 'hermes-skill-pick' },
      {
        origin: 'https://evil.example',
        source: frame.contentWindow
      }
    )

    expect(installCalls()).toEqual([])
  })

  it('regression: refuses identifiers outside the slug charset', () => {
    const frame = openHubBrowser()

    for (const identifier of ['../../etc/passwd', 'skill; rm -rf /', '-flag', 'name with spaces', '']) {
      postPick({ identifier, name: 'Web Research', type: 'hermes-skill-pick' }, { source: frame.contentWindow })
    }

    expect(installCalls()).toEqual([])
  })

  it('ignores messages that are not a skill pick', () => {
    const frame = openHubBrowser()

    postPick({ identifier: 'dragon-agent', type: 'oauth-callback' }, { source: frame.contentWindow })
    postPick({ identifier: 'dragon-agent', type: 'hermes-skill-pick' }, { source: frame.contentWindow })

    expect(installCalls()).toEqual([])
  })

  it('stops listening once the hub browser is closed', () => {
    const frame = openHubBrowser()

    fireEvent.click(screen.getByRole('button', { name: /hide the hub browser/i }))
    postPick(
      { identifier: 'dragon-agent', name: 'dragon-agent', type: 'hermes-skill-pick' },
      {
        source: frame.contentWindow
      }
    )

    expect(installCalls()).toEqual([])
  })
})
