import { useStore } from '@nanostores/react'
import { IconCheck, IconDeviceDesktop, IconUsersGroup } from '@tabler/icons-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { queryClient } from '@/lib/query-client'
import { cn } from '@/lib/utils'
import { $gateway } from '@/store/gateway'
import { notify, notifyError } from '@/store/notifications'

import { type MarketplaceTeam, seatProfileName, seatSoul, TEAMS_CATALOG } from './catalog'
import { $teamsMarketplaceOpen, closeTeamsMarketplace } from './store'

/** Bot Mode's plugin id: installed seats carry their look and section in that plugin's ui_meta slot. */
const BOTS_PLUGIN_ID = 'hermes-bots'

type InstallState = { status: 'done' } | { status: 'error' } | { status: 'installing'; done: number }

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
  const [selected, setSelected] = useState(TEAMS_CATALOG[0]!.slug)
  const [installs, setInstalls] = useState<Record<string, InstallState>>({})
  const team = TEAMS_CATALOG.find(entry => entry.slug === selected) ?? TEAMS_CATALOG[0]!
  const install = installs[team.slug]

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

  return (
    <Dialog onOpenChange={next => (next ? $teamsMarketplaceOpen.set(true) : closeTeamsMarketplace())} open={open}>
      <DialogContent
        bodyClassName="grid gap-0 p-0 overflow-hidden"
        className="max-w-[min(56rem,94vw)]"
        data-slot="dragon-teams-marketplace"
      >
        <DialogHeader className="border-b border-(--ui-stroke-tertiary) px-6 pt-5 pb-4">
          <DialogTitle>Teams Marketplace</DialogTitle>
          <DialogDescription>
            Install a ready-made team of bots. Each seat gets its own profile, role, and memory, and seats marked
            Computer get their own VM desktop.
          </DialogDescription>
        </DialogHeader>
        <div className="grid min-h-0 md:grid-cols-[17rem_1fr]">
          <div className="grid max-h-[22rem] content-start gap-1 overflow-y-auto border-b border-(--ui-stroke-tertiary) p-2 md:max-h-[60vh] md:border-r md:border-b-0">
            {TEAMS_CATALOG.map(entry => (
              <button
                className={cn(
                  'flex items-start gap-3 rounded-xl px-3 py-2.5 text-left transition-colors hover:bg-(--chrome-action-hover)',
                  entry.slug === team.slug && 'bg-(--ui-row-active-background)'
                )}
                key={entry.slug}
                onClick={() => setSelected(entry.slug)}
                type="button"
              >
                <span
                  className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full"
                  style={{ background: `${entry.accent}26`, color: entry.accent }}
                >
                  <IconUsersGroup className="size-4.5" stroke={1.75} />
                </span>
                <span className="min-w-0">
                  <span className="flex items-center gap-1.5">
                    <span className="truncate text-sm font-semibold">{entry.name}</span>
                    {installs[entry.slug]?.status === 'done' ? (
                      <IconCheck className="size-3.5 shrink-0 text-emerald-500" stroke={2.5} />
                    ) : null}
                  </span>
                  <span className="mt-0.5 line-clamp-2 block text-xs leading-4 text-(--ui-text-tertiary)">
                    {entry.tagline}
                  </span>
                </span>
              </button>
            ))}
          </div>
          <div className="grid max-h-[60vh] content-start gap-4 overflow-y-auto p-5">
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
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
