/** Workflow packs in the Teams Marketplace — skills/rules/commands, not bot seats. */

export const ECC_WORKFLOW_PACK_ID = 'ecc-workflows'

export interface WorkflowPack {
  accent: string
  description: string
  excluded: string[]
  included: string[]
  slug: string
  source: string
  tagline: string
  title: string
}

export const ECC_WORKFLOW_PACK: WorkflowPack = {
  slug: ECC_WORKFLOW_PACK_ID,
  title: 'ECC Workflows',
  tagline: 'Everything Claude Code — skills, rules, and commands.',
  description:
    'Install a curated workflow pack into this Dragon data folder. Skills show up under Capabilities → Skills. This is not a team of bots and does not add seats.',
  source: 'Everything Claude Code',
  accent: '#6f93cf',
  included: ['Skills', 'Rules', 'Commands'],
  excluded: ['Bot seats', 'Cursor hooks', 'Memory Vault']
}

export const WORKFLOW_PACKS: WorkflowPack[] = [ECC_WORKFLOW_PACK]

export const MARKETPLACE_INTRO =
  'Install a ready-made team of bots, or a workflow pack of skills, rules, and commands. Workflow packs go into this Dragon data folder — they are not a team of bots.'

export function workflowPackUserCopy(pack: WorkflowPack): string[] {
  return [pack.title, pack.tagline, pack.description, pack.source, ...pack.included, ...pack.excluded]
}

export function copyNamesFramework(text: string): boolean {
  return /\bhermes\b/i.test(text)
}

export type WorkflowPackAction = 'install' | 'remove' | 'update'

export function workflowPackProgressCopy(action: WorkflowPackAction): string {
  if (action === 'install') {
    return 'Installing ECC skills…'
  }

  if (action === 'update') {
    return 'Updating ECC skills…'
  }

  return 'Removing ECC Workflows…'
}

export function workflowPackSuccessCopy(action: WorkflowPackAction): string {
  if (action === 'remove') {
    return 'ECC Workflows removed from this Dragon data folder.'
  }

  const verb = action === 'update' ? 'updated' : 'installed'

  return `ECC Workflows ${verb}. Skills are under Capabilities → Skills.`
}
