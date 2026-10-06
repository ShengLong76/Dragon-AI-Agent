import { useStore } from '@nanostores/react'
import { IconCheck, IconDeviceDesktop, IconPackage, IconUsersGroup } from '@tabler/icons-react'
import { type ReactNode, useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { queryClient } from '@/lib/query-client'
import { cn } from '@/lib/utils'
import { $gateway } from '@/store/gateway'
import { notify, notifyError } from '@/store/notifications'

import { type MarketplaceTeam, seatProfileName, seatSoul, TEAMS_CATALOG } from './catalog'
import { getEccWorkflowStatus, runEccWorkflowAction } from './ecc-actions'
import { $teamsMarketplaceOpen, closeTeamsMarketplace } from './store'
import {
  ECC_WORKFLOW_PACK,
  ECC_WORKFLOW_PACK_ID,
  MARKETPLACE_INTRO,
  type WorkflowPack,
  type WorkflowPackAction,
  workflowPackProgressCopy,
  workflowPackSuccessCopy,
  WORKFLOW_PACKS
} from './workflow-packs'

import type { EccWorkflowStatus } from '@/hermes'

/** Bot Mode's plugin id: installed seats carry their look and section in that plugin's ui_meta slot. */
const BOTS_PLUGIN_ID = 'hermes-bots'

type InstallState = { status: 'done' } | { status: 'error' } | { status: 'installing'; done: number }

type MarketplaceSelection = { kind: 'pack'; slug: string } | { kind: 'team'; slug: string }

type PackActionState =
  | { status: 'done'; action: WorkflowPackAction }
  | { status: 'error'; action: WorkflowPackAction }
  | { status: 'idle' }
  | { status: 'running'; action: WorkflowPackAction }

const ALREADY_EXISTS = /exist/i

async function installTeam(team: MarketplaceTeam, onProgress: (done: number) => void) {
  const gateway = $gateway.get()

  if (!gateway) {
    throw new Error('Dragon AI is still connecting. Try again in a moment.')
  }

  const sectionId = `team-${team.slug}`
  let done = 0

  for (const seat of team.seats) {
    const name = seatProfileName(team, seat)

    try {
      await gateway.request('profiles.create', {
        name,
        description: seat.mission,
        clone_from: 'default',
        share_auth: true,
        soul: seatSoul(team, seat)
      })
    } catch (error) {
      if (!ALREADY_EXISTS.test(error instanceof Error ? error.message : String(error))) {
        throw error
      }
    }

    await gateway.request('profiles.configure', {
      name,
      ui_meta: {
        [BOTS_PLUGIN_ID]: {
          title: seat.title,
          role: seat.role,
          color: seat.color,
          shape: 'circle',
          imageKind: 'shape',
          sectionId,
          sectionName: team.name,
          created: Date.now()
        }
      }
    })

    done += 1
    onProgress(done)
  }

  await queryClient.invalidateQueries({ queryKey: [BOTS_PLUGIN_ID, 'roster'] })
}

export function TeamsMarketplaceDialog() {
  const open = useStore($teamsMarketplaceOpen)
  const [selected, setSelected] = useState<MarketplaceSelection>({
    kind: 'pack',
    slug: ECC_WORKFLOW_PACK_ID
  })
  const [installs, setInstalls] = useState<Record<string, InstallState>>({})
  const [eccStatus, setEccStatus] = useState<EccWorkflowStatus | null>(null)
  const [packAction, setPackAction] = useState<PackActionState>({ status: 'idle' })

  const team = selected.kind === 'team' ? (TEAMS_CATALOG.find(entry => entry.slug === selected.slug) ?? TEAMS_CATALOG[0]!) : null
  const pack = selected.kind === 'pack' ? (WORKFLOW_PACKS.find(entry => entry.slug === selected.slug) ?? ECC_WORKFLOW_PACK) : null
  const install = team ? installs[team.slug] : undefined

  useEffect(() => {
    if (!open) {
      return
    }

    let cancelled = false

    getEccWorkflowStatus()
      .then(status => {
        if (!cancelled) {
          setEccStatus(status)
        }
      })
      .catch(() => {
        if (!cancelled) {
          setEccStatus(null)
        }
      })

    return () => {
      cancelled = true
    }
  }, [open])

  const runInstall = (target: MarketplaceTeam) => {
    setInstalls(prev => ({ ...prev, [target.slug]: { status: 'installing', done: 0 } }))
    installTeam(target, done => setInstalls(prev => ({ ...prev, [target.slug]: { status: 'installing', done } })))
      .then(() => {
        setInstalls(prev => ({ ...prev, [target.slug]: { status: 'done' } }))
        notify({
          kind: 'success',
          message: `${target.name} installed: ${target.seats.length} bots added to the Bots tab.`
        })
      })
      .catch(error => {
        setInstalls(prev => ({ ...prev, [target.slug]: { status: 'error' } }))
        notifyError(error, `Couldn't install ${target.name}`)
      })
  }

  const runPack = (action: WorkflowPackAction) => {
    setPackAction({ status: 'running', action })
    runEccWorkflowAction(action)
      .then(() => getEccWorkflowStatus().catch(() => null))
      .then(status => {
        if (status) {
          setEccStatus(status)
        } else if (action === 'remove') {
          setEccStatus(prev => (prev ? { ...prev, installed: false, skill_count: 0, version: null } : prev))
        } else {
          setEccStatus(prev => (prev ? { ...prev, installed: true } : prev))
        }
        setPackAction({ status: 'done', action })
        notify({ kind: 'success', message: workflowPackSuccessCopy(action) })
      })
      .catch(error => {
        setPackAction({ status: 'error', action })
        notifyError(error, `Couldn't ${action} ${ECC_WORKFLOW_PACK.title}`)
      })
  }

  return (
    <Dialog onOpenChange={next => (next ? $teamsMarketplaceOpen.set(true) : closeTeamsMarketplace())} open={open}>
      <DialogContent
        bodyClassName="grid gap-0 p-0 overflow-hidden"
        className="max-w-[min(56rem,94vw)]"
        data-slot="dragon-teams-marketplace"
      >
        <DialogHeader className="border-b border-(--ui-stroke-tertiary) px-6 pt-5 pb-4">
          <DialogTitle>Teams Marketplace</DialogTitle>
          <DialogDescription>{MARKETPLACE_INTRO}</DialogDescription>
        </DialogHeader>
        <div className="grid min-h-0 md:grid-cols-[17rem_1fr]">
          <div className="grid max-h-[22rem] content-start gap-1 overflow-y-auto border-b border-(--ui-stroke-tertiary) p-2 md:max-h-[60vh] md:border-r md:border-b-0">
            <div className="px-3 pt-1.5 pb-1 text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-(--ui-text-tertiary)">
              Workflow packs
            </div>
            {WORKFLOW_PACKS.map(entry => (
              <MarketplaceListButton
                accent={entry.accent}
                active={selected.kind === 'pack' && selected.slug === entry.slug}
                done={Boolean(eccStatus?.installed) || (packAction.status === 'done' && packAction.action !== 'remove')}
                icon={<IconPackage className="size-4.5" stroke={1.75} />}
                key={entry.slug}
                onSelect={() => setSelected({ kind: 'pack', slug: entry.slug })}
                subtitle={entry.tagline}
                title={entry.title}
              />
            ))}
            <div className="px-3 pt-3 pb-1 text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-(--ui-text-tertiary)">
              Teams
            </div>
            {TEAMS_CATALOG.map(entry => (
              <MarketplaceListButton
                accent={entry.accent}
                active={selected.kind === 'team' && selected.slug === entry.slug}
                done={installs[entry.slug]?.status === 'done'}
                icon={<IconUsersGroup className="size-4.5" stroke={1.75} />}
                key={entry.slug}
                onSelect={() => setSelected({ kind: 'team', slug: entry.slug })}
                subtitle={entry.tagline}
                title={entry.name}
              />
            ))}
          </div>
          <div className="grid max-h-[60vh] content-start gap-4 overflow-y-auto p-5">
            {pack ? (
              <WorkflowPackDetail eccStatus={eccStatus} pack={pack} packAction={packAction} runPack={runPack} />
            ) : team ? (
              <TeamDetail install={install} runInstall={runInstall} team={team} />
            ) : null}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function MarketplaceListButton({
  accent,
  active,
  done,
  icon,
  onSelect,
  subtitle,
  title
}: {
  accent: string
  active: boolean
  done: boolean
  icon: ReactNode
  onSelect: () => void
  subtitle: string
  title: string
}) {
  return (
    <button
      className={cn(
        'flex items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-(--chrome-action-hover)',
        active && 'bg-(--ui-row-active-background)'
      )}
      onClick={onSelect}
      type="button"
    >
      <span
        className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full"
        style={{ background: `${accent}26`, color: accent }}
      >
        {icon}
      </span>
      <span className="min-w-0">
        <span className="flex items-center gap-1.5">
          <span className="truncate text-sm font-semibold">{title}</span>
          {done ? <IconCheck className="size-3.5 shrink-0 text-emerald-500" stroke={2.5} /> : null}
        </span>
        <span className="mt-0.5 line-clamp-2 block text-xs leading-4 text-(--ui-text-tertiary)">{subtitle}</span>
      </span>
    </button>
  )
}

function WorkflowPackDetail({
  eccStatus,
  pack,
  packAction,
  runPack
}: {
  eccStatus: EccWorkflowStatus | null
  pack: WorkflowPack
  packAction: PackActionState
  runPack: (action: WorkflowPackAction) => void
}) {
  const installed = Boolean(eccStatus?.installed)
  const running = packAction.status === 'running'
  const skillCount = eccStatus?.skill_count ?? 0
  const version = eccStatus?.version

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 max-w-xl">
          <div className="text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-(--ui-text-tertiary)">
            Workflow pack · {pack.source}
          </div>
          <h3 className="mt-1 text-lg font-semibold tracking-tight">{pack.title}</h3>
          <p className="mt-1 text-[0.8125rem] leading-5 text-(--ui-text-secondary)">{pack.description}</p>
          {installed ? (
            <p className="mt-2 text-xs text-(--ui-text-tertiary)">
              Installed in this Dragon data folder
              {version ? ` · ${version}` : ''}
              {skillCount > 0 ? ` · ${skillCount} skill${skillCount === 1 ? '' : 's'}` : ''}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {running ? (
            <Button disabled variant="default">
              {workflowPackProgressCopy(packAction.action)}
            </Button>
          ) : installed ? (
            <>
              <Button onClick={() => runPack('update')} variant={packAction.status === 'done' && packAction.action === 'update' ? 'secondary' : 'default'}>
                {packAction.status === 'error' && packAction.action === 'update' ? 'Retry update' : 'Update'}
              </Button>
              <Button onClick={() => runPack('remove')} variant="secondary">
                {packAction.status === 'error' && packAction.action === 'remove' ? 'Retry remove' : 'Remove'}
              </Button>
            </>
          ) : (
            <Button onClick={() => runPack('install')} variant={packAction.status === 'done' ? 'secondary' : 'default'}>
              {packAction.status === 'error' && packAction.action === 'install' ? 'Retry install' : 'Install'}
            </Button>
          )}
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="grid gap-2 rounded-2xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/40 p-3.5">
          <div className="text-xs font-semibold text-(--ui-text-secondary)">Includes</div>
          <ul className="grid gap-1.5 text-sm text-(--ui-text-secondary)">
            {pack.included.map(item => (
              <li className="flex items-center gap-2" key={item}>
                <IconCheck className="size-3.5 text-emerald-500" stroke={2.5} />
                {item}
              </li>
            ))}
          </ul>
        </div>
        <div className="grid gap-2 rounded-2xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/40 p-3.5">
          <div className="text-xs font-semibold text-(--ui-text-secondary)">Not included</div>
          <ul className="grid gap-1.5 text-sm text-(--ui-text-tertiary)">
            {pack.excluded.map(item => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </>
  )
}

function TeamDetail({
  install,
  runInstall,
  team
}: {
  install: InstallState | undefined
  runInstall: (team: MarketplaceTeam) => void
  team: MarketplaceTeam
}) {
  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 max-w-xl">
          <div className="text-[0.6875rem] font-semibold uppercase tracking-[0.16em] text-(--ui-text-tertiary)">
            {team.category} · {team.seats.length} seats
          </div>
          <h3 className="mt-1 text-lg font-semibold tracking-tight">{team.name}</h3>
          <p className="mt-1 text-[0.8125rem] leading-5 text-(--ui-text-secondary)">{team.description}</p>
        </div>
        <Button
          disabled={install?.status === 'installing'}
          onClick={() => runInstall(team)}
          variant={install?.status === 'done' ? 'secondary' : 'default'}
        >
          {install?.status === 'installing'
            ? `Installing ${install.done}/${team.seats.length}…`
            : install?.status === 'done'
              ? 'Installed'
              : install?.status === 'error'
                ? 'Retry install'
                : 'Install team'}
        </Button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        {team.seats.map(seat => (
          <div
            className="grid gap-2 rounded-2xl border border-(--ui-stroke-tertiary) bg-(--ui-bg-tertiary)/40 p-3.5"
            key={seat.slug}
          >
            <div className="flex items-center gap-3">
              <span
                className="grid size-10 shrink-0 place-items-center rounded-full text-sm font-bold text-white"
                style={{ background: seat.color }}
              >
                {seat.title.slice(0, 1)}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold">{seat.title}</span>
                <span className="mt-0.5 inline-flex items-center gap-1.5">
                  <span className="rounded-full bg-(--ui-bg-tertiary) px-2 py-px text-[0.6875rem] font-medium text-(--ui-text-tertiary)">
                    {seat.role}
                  </span>
                  {seat.computer ? (
                    <span className="inline-flex items-center gap-1 text-[0.6875rem] text-(--ui-text-tertiary)">
                      <IconDeviceDesktop className="size-3" stroke={2} />
                      Computer
                    </span>
                  ) : null}
                </span>
              </span>
            </div>
            <p className="text-xs leading-[1.125rem] text-(--ui-text-secondary)">{seat.mission}</p>
          </div>
        ))}
      </div>
    </>
  )
}
