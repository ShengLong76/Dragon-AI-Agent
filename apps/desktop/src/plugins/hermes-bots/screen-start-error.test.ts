import { expect, it } from 'vitest'

import { friendlyScreenStartError, isLeftoverDisplayError } from './screen-start-error'

const leftover =
  'The sandbox screen could not start. A leftover display from a previous run was still in the container — click Start screen again.'

it('replaces the raw Xvnc leftover-lock dump with the friendly Computer copy', () => {
  const raw =
    'sandbox desktop did not publish its display within 20s:\n' +
    '(EE) Fatal server error:\n' +
    '(EE) Server is already active for display 20\n' +
    'If this server is no longer running, remove /tmp/.X20-lock and start again.\n' +
    '(EE) Xvnc exited during startup'
  expect(isLeftoverDisplayError(raw)).toBe(true)
  expect(friendlyScreenStartError(raw, leftover)).toBe(leftover)
  expect(friendlyScreenStartError(raw, leftover)).not.toMatch(/\(EE\)/)
})

it('keeps an unrelated start error so the operator can act on it', () => {
  const raw = 'Bot Desktop needs Xvnc inside the terminal backend\'s sandbox'
  expect(isLeftoverDisplayError(raw)).toBe(false)
  expect(friendlyScreenStartError(raw, leftover)).toBe(raw)
})
