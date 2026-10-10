import assert from 'node:assert/strict'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { test } from 'vitest'

import { githubAppUpdateYml, writeGitHubAppUpdateYml } from './write-github-app-update-yml.mjs'

test('the packaged app-update.yml is Dragon GitHub Releases', () => {
  const text = githubAppUpdateYml()
  assert.match(text, /^provider: github$/m)
  assert.match(text, /^owner: ShengLong76$/m)
  assert.match(text, /^repo: Dragon-AI-Agent$/m)
  assert.doesNotMatch(text, /NousResearch|hermes-agent|hermes-assets/i)
})

test('writes app-update.yml into the packaged resources directory', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'app-update-'))
  try {
    const dest = writeGitHubAppUpdateYml(dir)
    assert.equal(dest, path.join(dir, 'app-update.yml'))
    assert.match(fs.readFileSync(dest, 'utf8'), /Dragon-AI-Agent/)
  } finally {
    fs.rmSync(dir, { recursive: true, force: true })
  }
})
