import { beforeEach, describe, expect, it, vi } from 'vitest'

const getActionStatus = vi.fn()
const installEccWorkflows = vi.fn()
const updateEccWorkflows = vi.fn()
const removeEccWorkflows = vi.fn()
const invalidateQueries = vi.fn()
const invalidateSlashCompletions = vi.fn()
const skillsReload = vi.fn()

vi.mock('@/hermes', () => ({
  getActionStatus: (...args: unknown[]) => getActionStatus(...args),
  installEccWorkflows: (...args: unknown[]) => installEccWorkflows(...args),
  updateEccWorkflows: (...args: unknown[]) => updateEccWorkflows(...args),
  removeEccWorkflows: (...args: unknown[]) => removeEccWorkflows(...args),
  getEccWorkflowStatus: vi.fn()
}))

vi.mock('@/lib/query-client', () => ({
  queryClient: { invalidateQueries: (...args: unknown[]) => invalidateQueries(...args) }
}))

vi.mock('@/lib/slash-completion-cache', () => ({
  invalidateSlashCompletions: () => invalidateSlashCompletions()
}))

vi.mock('@/store/gateway', () => ({
  $gateway: { get: () => ({ request: (...args: unknown[]) => skillsReload(...args) }) }
}))

vi.mock('@/store/hub-actions', () => ({
  HUB_SOURCES_KEY: ['skill-hub-sources'],
  OFFICIAL_SKILLS_KEY: ['official-skills']
}))

vi.mock('@/app/capabilities/skills/skills-data', () => ({
  SKILLS_QUERY_KEY: ['skills-list']
}))

import { runEccWorkflowAction } from './ecc-actions'

describe('runEccWorkflowAction', () => {
  beforeEach(() => {
    getActionStatus.mockReset()
    installEccWorkflows.mockReset()
    updateEccWorkflows.mockReset()
    removeEccWorkflows.mockReset()
    invalidateQueries.mockReset()
    invalidateSlashCompletions.mockReset()
    skillsReload.mockReset()
  })

  it('installs, waits for a clean exit, and invalidates skills caches', async () => {
    installEccWorkflows.mockResolvedValue({ name: 'ecc-workflows-install' })
    getActionStatus.mockResolvedValue({
      name: 'ecc-workflows-install',
      running: false,
      exit_code: 0,
      lines: ['Installing ECC skills…']
    })
    skillsReload.mockResolvedValue({})

    await runEccWorkflowAction('install')

    expect(installEccWorkflows).toHaveBeenCalled()
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: ['skills-list'] })
    expect(invalidateSlashCompletions).toHaveBeenCalled()
    expect(skillsReload).toHaveBeenCalledWith('skills.reload', {})
  })

  it('rejects when the installer exits non-zero', async () => {
    installEccWorkflows.mockResolvedValue({ name: 'ecc-workflows-install' })
    getActionStatus.mockResolvedValue({
      name: 'ecc-workflows-install',
      running: false,
      exit_code: 1,
      lines: ['npx: command not found']
    })

    await expect(runEccWorkflowAction('install')).rejects.toThrow('npx: command not found')
    expect(invalidateSlashCompletions).not.toHaveBeenCalled()
  })

  it('update and remove wait on their own action names', async () => {
    updateEccWorkflows.mockResolvedValue({ name: 'ecc-workflows-update' })
    removeEccWorkflows.mockResolvedValue({ name: 'ecc-workflows-uninstall' })
    getActionStatus.mockResolvedValue({
      running: false,
      exit_code: 0,
      lines: []
    })

    await runEccWorkflowAction('update')
    expect(updateEccWorkflows).toHaveBeenCalled()
    expect(getActionStatus).toHaveBeenCalledWith('ecc-workflows-update', 200, undefined)

    await runEccWorkflowAction('remove')
    expect(removeEccWorkflows).toHaveBeenCalled()
    expect(getActionStatus).toHaveBeenCalledWith('ecc-workflows-uninstall', 200, undefined)
  })
})
