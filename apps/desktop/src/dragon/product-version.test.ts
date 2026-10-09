import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

import {
  DRAGON_PRODUCT_VERSION,
  dragonProductVersionLabel,
  isDragonProductVersion,
  sanitizeRuntimeVersion
} from './product-version'

const here = dirname(fileURLToPath(import.meta.url))
const desktopRoot = resolve(here, '../..')
const repoRoot = resolve(desktopRoot, '../..')

describe('Dragon product version', () => {
  it('reads the desktop package version and matches the product feed', () => {
    const desktop = JSON.parse(readFileSync(resolve(desktopRoot, 'package.json'), 'utf8')) as { version: string }
    const feed = JSON.parse(readFileSync(resolve(repoRoot, 'branding/product-feed.json'), 'utf8')) as {
      productVersion: string
    }

    expect(DRAGON_PRODUCT_VERSION).toBe(desktop.version)
    expect(feed.productVersion).toBe(desktop.version)
    expect(dragonProductVersionLabel()).toBe(`v${desktop.version}`)
  })

  it('never treats a Hermes-era runtime string as the Dragon product', () => {
    expect(isDragonProductVersion('0.21.5+9105')).toBe(false)
    expect(isDragonProductVersion('v0.21.5+9105.gabc1234')).toBe(false)
    expect(sanitizeRuntimeVersion('0.21.5+9105')).toBeNull()
    expect(sanitizeRuntimeVersion(DRAGON_PRODUCT_VERSION)).toBe(DRAGON_PRODUCT_VERSION)
    expect(sanitizeRuntimeVersion(`v${DRAGON_PRODUCT_VERSION}+2.gdef`)).toBe(`${DRAGON_PRODUCT_VERSION}+2`)
  })
})
