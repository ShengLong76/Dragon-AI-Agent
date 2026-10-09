import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'vitest'

import {
  findForbiddenShippedAssets,
  isForbiddenShippedAsset,
} from './forbidden-shipped-assets.mjs'

test('only image/asset names matching nous|girl|hermes are forbidden', () => {
  assert.equal(isForbiddenShippedAsset('nous-girl.png'), true)
  assert.equal(isForbiddenShippedAsset('public/nous-girl-dark.png'), true)
  assert.equal(isForbiddenShippedAsset('website/static/img/nous-logo.png'), true)
  assert.equal(isForbiddenShippedAsset('hermes-frames/hermes-frame-0.png'), true)
  assert.equal(isForbiddenShippedAsset('hermes.png'), true)
  assert.equal(isForbiddenShippedAsset('dragon-logo.png'), false)
  assert.equal(isForbiddenShippedAsset('apple-touch-icon.png'), false)
  assert.equal(isForbiddenShippedAsset('dragon-build.json'), false)
  assert.equal(isForbiddenShippedAsset('assets/index-abc.js'), false)
})

test('findForbiddenShippedAssets reports leftover files in a tree', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'forbidden-assets-'))
  try {
    fs.mkdirSync(path.join(root, 'dist'), { recursive: true })
    fs.writeFileSync(path.join(root, 'dist', 'dragon-logo.png'), 'ok')
    fs.writeFileSync(path.join(root, 'dist', 'nous-girl.png'), 'stale')
    fs.mkdirSync(path.join(root, 'dist', 'hermes-frames'))
    fs.writeFileSync(path.join(root, 'dist', 'hermes-frames', 'hermes-frame-1.png'), 'stale')
    assert.deepEqual(findForbiddenShippedAssets(root).sort(), [
      'dist/hermes-frames/hermes-frame-1.png',
      'dist/nous-girl.png',
    ])
  } finally {
    fs.rmSync(root, { recursive: true, force: true })
  }
})
