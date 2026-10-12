import { describe, expect, it } from 'vitest'

import {
  copyNamesFramework,
  ECC_WORKFLOW_PACK,
  ECC_WORKFLOW_PACK_ID,
  MARKETPLACE_INTRO,
  WORKFLOW_PACKS,
  workflowPackProgressCopy,
  workflowPackSuccessCopy,
  workflowPackUserCopy
} from './workflow-packs'

describe('ECC workflow pack catalog', () => {
  it('is a workflow pack, not a bot-seat team', () => {
    expect(ECC_WORKFLOW_PACK.slug).toBe(ECC_WORKFLOW_PACK_ID)
    expect(ECC_WORKFLOW_PACK.title).toBe('ECC Workflows')
    expect(ECC_WORKFLOW_PACK.included).toEqual(['Skills', 'Rules', 'Commands'])
    expect(ECC_WORKFLOW_PACK.excluded).toContain('Bot seats')
    expect(ECC_WORKFLOW_PACK.excluded).toContain('Memory Vault')
    expect(ECC_WORKFLOW_PACK.excluded).toContain('Cursor hooks')
    expect(WORKFLOW_PACKS).toContainEqual(ECC_WORKFLOW_PACK)
    expect(ECC_WORKFLOW_PACK).not.toHaveProperty('seats')
  })

  it('never names the underlying framework in user-facing copy', () => {
    for (const line of workflowPackUserCopy(ECC_WORKFLOW_PACK)) {
      expect(copyNamesFramework(line), line).toBe(false)
    }

    expect(copyNamesFramework('Dragon data folder')).toBe(false)
    expect(copyNamesFramework('Installing ECC skills…')).toBe(false)
    expect(copyNamesFramework(MARKETPLACE_INTRO)).toBe(false)
    expect(MARKETPLACE_INTRO).toContain('workflow pack')
    expect(MARKETPLACE_INTRO).toContain('Dragon data folder')

    for (const action of ['install', 'update', 'remove'] as const) {
      expect(copyNamesFramework(workflowPackProgressCopy(action)), action).toBe(false)
      expect(copyNamesFramework(workflowPackSuccessCopy(action)), action).toBe(false)
    }
  })

  it('uses the install-progress and Capabilities toast copy from the journey', () => {
    expect(workflowPackProgressCopy('install')).toBe('Installing ECC skills…')
    expect(workflowPackSuccessCopy('install')).toContain('Capabilities → Skills')
    expect(workflowPackSuccessCopy('remove')).toContain('Dragon data folder')
  })
})
