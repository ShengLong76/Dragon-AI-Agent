import { SKILLS_QUERY_KEY } from '@/app/capabilities/skills/skills-data'
import {
  getActionStatus,
  getEccWorkflowStatus,
  installEccWorkflows,
  type ProfileScope,
  removeEccWorkflows,
  updateEccWorkflows
} from '@/hermes'
import { queryClient } from '@/lib/query-client'
import { invalidateSlashCompletions } from '@/lib/slash-completion-cache'
import { $gateway } from '@/store/gateway'
import { HUB_SOURCES_KEY, OFFICIAL_SKILLS_KEY } from '@/store/hub-actions'

const POLL_MS = 1200

export type EccWorkflowAction = 'install' | 'remove' | 'update'

async function waitForAction(name: string, profile?: ProfileScope): Promise<void> {
  for (;;) {
    const status = await getActionStatus(name, 200, profile)

    if (!status.running) {
      if (status.exit_code !== null && status.exit_code !== 0) {
        const detail = status.lines.slice(-3).join('\n').trim()

        throw new Error(detail || `Action exited with code ${status.exit_code}`)
      }

      return
    }

    await new Promise(resolve => setTimeout(resolve, POLL_MS))
  }
}

export async function refreshAfterEccChange(): Promise<void> {
  void queryClient.invalidateQueries({ queryKey: SKILLS_QUERY_KEY })
  void queryClient.invalidateQueries({ queryKey: HUB_SOURCES_KEY })
  void queryClient.invalidateQueries({ queryKey: OFFICIAL_SKILLS_KEY })
  invalidateSlashCompletions()

  const gateway = $gateway.get()

  if (gateway) {
    try {
      await gateway.request('skills.reload', {})
    } catch {
      // Older backends or a disconnected socket: the skills list refetch is enough.
    }
  }
}

export async function runEccWorkflowAction(action: EccWorkflowAction, profile?: ProfileScope): Promise<void> {
  const spawn =
    action === 'install' ? installEccWorkflows : action === 'update' ? updateEccWorkflows : removeEccWorkflows

  const started = await spawn(profile)

  await waitForAction(started.name, profile)
  await refreshAfterEccChange()
}

export { getEccWorkflowStatus }
