import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { afterEach, test } from 'vitest'

const require: NodeJS.Require = createRequire(import.meta.url)

afterEach((): void => {
  delete process.env.GITHUB_REPOSITORY
  delete process.env.CLOUDFLARE_R2_PUBLIC_URL
  delete process.env.HERMES_PAYLOAD_TAG
  delete process.env.HERMES_BUILD_COMMIT
  delete process.env.HERMES_DESKTOP_VARIANT
  delete require.cache[require.resolve('../update-feed.cjs')]
  delete require.cache[require.resolve('../electron-builder.config.cjs')]
  delete require.cache[require.resolve('../product-identity.cjs')]
})

test('the packaged updater feed is Dragon GitHub Releases, never Hermes', (): void => {
  const feed: {
    productRepository: () => string
    upstreamRepository: () => string
    isUpstreamRepository: (value: string) => boolean
    packagedFeedBaseUrl: (envUrl?: string) => string | undefined
  } = require('../update-feed.cjs')

  assert.equal(feed.productRepository(), 'ShengLong76/Dragon-AI-Agent')
  assert.equal(feed.upstreamRepository(), 'NousResearch/hermes-agent')
  assert.equal(feed.isUpstreamRepository('NousResearch/hermes-agent'), true)
  assert.equal(feed.packagedFeedBaseUrl('https://hermes-assets.nousresearch.com'), undefined)

  delete process.env.GITHUB_REPOSITORY
  delete process.env.CLOUDFLARE_R2_PUBLIC_URL
  process.env.HERMES_PAYLOAD_TAG = 'v0.28.0+canary.20260818T000000Z'
  process.env.HERMES_DESKTOP_VARIANT = 'bundled'
  const config: { publish: Array<{ provider: string; owner?: string; repo?: string; url?: string }> } =
    require('../electron-builder.config.cjs')

  assert.ok(Array.isArray(config.publish))
  assert.equal(config.publish[0]?.provider, 'github')
  assert.equal(config.publish[0]?.owner, 'ShengLong76')
  assert.equal(config.publish[0]?.repo, 'Dragon-AI-Agent')
  assert.equal(config.publish[0]?.url, undefined)
})
