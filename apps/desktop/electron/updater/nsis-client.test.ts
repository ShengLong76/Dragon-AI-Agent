import { afterEach, expect, it, vi } from 'vitest'

const { client } = vi.hoisted(() => ({
  client: {
    autoDownload: true,
    autoInstallOnAppQuit: true,
    autoRunAppAfterInstall: false,
    channel: '',
    allowPrerelease: true,
    allowDowngrade: true,
    on: vi.fn(),
    setFeedURL: vi.fn()
  }
}))

vi.mock('electron-updater', () => ({
  default: {
    NsisUpdater: class {
      constructor() {
        return client
      }
    }
  }
}))

import { createNsisStrategy } from './nsis-client'

afterEach((): void => {
  vi.clearAllMocks()
})

it('points the Windows updater at Dragon GitHub Releases, never Hermes', (): void => {
  const strategy = createNsisStrategy({
    channel: 'latest',
    light: false,
    feedBaseUrl: '',
    appVersion: '0.3.0',
    log: vi.fn(),
    emitProgress: vi.fn(),
    beforeInstall: vi.fn(),
    onInstallFailure: vi.fn()
  })

  expect(strategy.mechanism).toBe('electron-updater')
  expect(client.autoDownload).toBe(false)
  expect(client.allowPrerelease).toBe(false)
  expect(client.setFeedURL).toHaveBeenCalledWith({
    provider: 'github',
    owner: 'ShengLong76',
    repo: 'Dragon-AI-Agent',
    channel: 'latest'
  })
})

it('refuses a leftover CDN feed base so Hermes R2 cannot be baked in', (): void => {
  expect((): ReturnType<typeof createNsisStrategy> =>
    createNsisStrategy({
      channel: 'latest',
      light: false,
      feedBaseUrl: 'https://hermes-assets.nousresearch.com',
      appVersion: '0.3.0',
      log: vi.fn(),
      emitProgress: vi.fn(),
      beforeInstall: vi.fn(),
      onInstallFailure: vi.fn()
    })
  ).toThrow(/GitHub Releases feed/)
})
