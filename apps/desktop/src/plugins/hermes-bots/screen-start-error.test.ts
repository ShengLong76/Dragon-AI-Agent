import { expect, it } from 'vitest'

import {
  friendlyScreenStartError,
  isLeftoverDisplayError,
  isOpaqueGatewayStartError
} from './screen-start-error'

const leftover =
  'The sandbox screen could not start. A leftover display from a previous run was still in the container — click Start screen again.'

const docker =
  'The screen did not start. Docker may not be running, or the sandbox image is missing. Start Docker Desktop, then click Start screen again.'

it('replaces the raw Xvnc leftover-lock dump with the friendly Computer copy', () => {
  const raw =
    'sandbox desktop did not publish its display within 20s:\n' +
    '(EE) Fatal server error:\n' +
    '(EE) Server is already active for display 20\n' +
    'If this server is no longer running, remove /tmp/.X20-lock and start again.\n' +
    '(EE) Xvnc exited during startup'

  expect(isLeftoverDisplayError(raw)).toBe(true)
  expect(friendlyScreenStartError(raw, leftover, docker)).toBe(leftover)
  expect(friendlyScreenStartError(raw, leftover, docker)).not.toMatch(/\(EE\)/)
})

it('keeps an unrelated start error so the operator can act on it', () => {
  const raw = "Bot Desktop needs Xvnc inside the terminal backend's sandbox"
  expect(isLeftoverDisplayError(raw)).toBe(false)
  expect(friendlyScreenStartError(raw, leftover, docker)).toBe(raw)
})

it('keeps the real image-missing and docker-daemon errors', () => {
  const image =
    "Bot Desktop cannot start: sandbox image 'dragon-sandbox:desktop' is not available locally " +
    "and every fallback failed. Fix: `docker pull nousresearch/hermes-sandbox:desktop`"

  const daemon = 'Docker daemon is not responding. Ensure Docker is running and try again.'
  expect(isOpaqueGatewayStartError(image)).toBe(false)
  expect(isOpaqueGatewayStartError(daemon)).toBe(false)
  expect(friendlyScreenStartError(image, leftover, docker)).toBe(image)
  expect(friendlyScreenStartError(daemon, leftover, docker)).toBe(daemon)
})

it('replaces a heartbeat-closed start with the docker/image retry copy', () => {
  expect(isOpaqueGatewayStartError('Dragon AI gateway connection closed')).toBe(true)
  expect(friendlyScreenStartError('Dragon AI gateway connection closed', leftover, docker)).toBe(docker)
  expect(friendlyScreenStartError('request timed out after 30s: display.start', leftover, docker)).toBe(docker)
})
