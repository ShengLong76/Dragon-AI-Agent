import electronUpdater from 'electron-updater'

import feedContract from '../../update-feed.cjs'

import { MacStrategy, type MacStrategyDeps } from './mac'

export interface NsisClientDeps extends Omit<MacStrategyDeps, 'updater' | 'prepareInstall'> {
  light: boolean
  feedBaseUrl: string
  log: (message: string) => void
}

export function createNsisStrategy(deps: NsisClientDeps): MacStrategy {
  const channel = deps.channel === 'canary' || deps.channel === 'light-canary' ? 'canary' : 'latest'
  const updater = new electronUpdater.NsisUpdater()

  updater.autoDownload = false
  updater.autoInstallOnAppQuit = false
  updater.autoRunAppAfterInstall = true
  updater.channel = channel
  updater.allowPrerelease = false
  updater.allowDowngrade = false
  updater.on('error', error => deps.log(`Windows updater: ${error.message}`))

  if (deps.feedBaseUrl) {
    throw new Error('Dragon Windows updates use the packaged GitHub Releases feed')
  }

  const [owner, repo] = feedContract.productRepository().split('/')
  if (!owner || !repo) {
    throw new Error('packaged Windows feed is missing ShengLong76/Dragon-AI-Agent')
  }
  updater.setFeedURL({ provider: 'github', owner, repo, channel })

  return new MacStrategy({
    ...deps,
    updater,
    prepareInstall: async (): Promise<void> => {
      // NSIS applies on quitAndInstall; there is no Squirrel.Mac verify step.
    }
  })
}
