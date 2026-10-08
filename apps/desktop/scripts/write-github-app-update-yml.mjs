/**
 * Bake the Dragon GitHub Releases feed into the packaged app without
 * instantiating electron-builder's GitHubPublisher (that constructor
 * demands GH_TOKEN even when `--publish never`).
 */
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)

export function githubAppUpdateYml(feed = require('../update-feed.cjs')) {
  const [owner, repo] = feed.productRepository().split('/')
  if (owner !== 'ShengLong76' || repo !== 'Dragon-AI-Agent') {
    throw new Error(`packaged feed must be ShengLong76/Dragon-AI-Agent, got ${owner}/${repo}`)
  }
  if (feed.packagedFeedBaseUrl(process.env.CLOUDFLARE_R2_PUBLIC_URL)) {
    throw new Error('packaged feed must not use an assets CDN')
  }
  return [
    'provider: github',
    `owner: ${owner}`,
    `repo: ${repo}`,
    'channel: latest',
    'updaterCacheDirName: dragon-ai-updater',
    ''
  ].join('\n')
}

export function writeGitHubAppUpdateYml(resourcesDir, feed) {
  const dest = path.join(resourcesDir, 'app-update.yml')
  fs.mkdirSync(resourcesDir, { recursive: true })
  fs.writeFileSync(dest, githubAppUpdateYml(feed), 'utf8')
  return dest
}
