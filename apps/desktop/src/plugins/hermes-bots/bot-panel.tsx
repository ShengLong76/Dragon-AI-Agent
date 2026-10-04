/**
 * The right-sidebar Bot panel: one bot's identity card with Details | Library |
 * Computer tabs. Double-clicking a roster row (or a pinned tile) opens it on
 * the Computer tab — the bot's VM desktop — rather than a file list.
 */

import { atom, Button, cn, Codicon, GlyphSpinner, host, PanelEmpty, useValue } from '@hermes/plugin-sdk'
import { useState } from 'react'

import { avatarColor, botAppearance, BotFace } from './avatar'
import { $lastJobs, RoutineDetailDialog, RoutineRow, selectRoutineJobs, useRoutines } from './cron'
import { $botMeta, $lastRoster, botSelectionKey } from './data'
import { botRole, displayName } from './labels'
import { botRosterMeta } from './routing'
import { BotScreenPane } from './screen-pane'
import { ID } from './shared'
import { HubSkillsSection } from './skills-hub'
import type { RosterRow } from './types'

export type BotPanelTab = 'computer' | 'details' | 'library'

export const BOT_PANEL_PANE_ID = `${ID}:bot-panel`

export const $botPanel = atom<{ key: string; tab: BotPanelTab } | null>(null)

export function openBotPanel(bot: RosterRow, tab: BotPanelTab = 'computer') {
  $botPanel.set({ key: botSelectionKey(bot), tab })
  host.revealPane(BOT_PANEL_PANE_ID)
}

const TABS: { id: BotPanelTab; label: string }[] = [
  { id: 'details', label: 'Details' },
  { id: 'library', label: 'Library' },
  { id: 'computer', label: 'Computer' }
]

export function BotPanelPane() {
  const panel = useValue($botPanel)
  const roster = useValue($lastRoster)
  const allMeta = useValue($botMeta)
  const bot = panel ? roster.find(row => botSelectionKey(row) === panel.key) : null

  if (!panel || !bot) {
    return (
      <PanelEmpty
        description="Double-click a bot in the Bots tab to open its computer, details, and library here."
        icon="hubot"
        title="No bot open"
      />
    )
  }

  const meta = botRosterMeta(bot, allMeta)
  const { shape, color, image } = botAppearance(bot.name, meta)
  const setTab = (tab: BotPanelTab) => $botPanel.set({ key: panel.key, tab })

  return (
    <div className="flex h-full min-h-0 flex-col" data-slot="dragon-bot-panel">
      <div className="grid justify-items-center gap-2 px-4 pt-6 pb-4 text-center">
        <div className="grid size-24 place-items-center overflow-hidden rounded-full bg-(--ui-bg-tertiary) ring-1 ring-(--ui-stroke-tertiary)">
          <BotFace color={avatarColor(color, bot.name)} image={image} name={bot.name} shape={shape} size={72} />
        </div>
        <div className="max-w-full truncate text-lg font-semibold tracking-tight">{displayName(bot, meta)}</div>
        <span className="rounded-full bg-(--ui-bg-tertiary) px-2.5 py-0.5 text-xs font-medium text-(--ui-text-secondary)">
          {botRole(bot, meta)}
        </span>
      </div>
      <div className="mx-3 flex gap-1 rounded-full bg-(--ui-bg-tertiary)/60 p-1" role="tablist">
        {TABS.map(tab => (
          <button
            aria-selected={panel.tab === tab.id}
            className={cn(
              'flex-1 rounded-full px-3 py-1.5 text-[0.8125rem] font-medium transition-colors',
              panel.tab === tab.id
                ? 'bg-(--ui-row-active-background) text-foreground'
                : 'text-(--ui-text-tertiary) hover:text-foreground'
            )}
            key={tab.id}
            onClick={() => setTab(tab.id)}
            role="tab"
            type="button"
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="mt-2 min-h-0 flex-1 overflow-hidden">
        {panel.tab === 'computer' ? (
          <BotScreenPane bot={bot} key={panel.key} />
        ) : panel.tab === 'library' ? (
          <div className="h-full overflow-y-auto px-3 py-2">
            <HubSkillsSection bot={bot} />
          </div>
        ) : (
          <BotDetails bot={bot} description={meta?.description || bot.description || ''} />
        )}
      </div>
    </div>
  )
}

function BotDetails({ bot, description }: { bot: RosterRow; description: string }) {
  const { data, error, isLoading } = useRoutines(bot)
  const [detailJobId, setDetailJobId] = useState<null | string>(null)
  const view = selectRoutineJobs(data, error, $lastJobs.get(), bot.name)
  const detailJob = detailJobId ? view.jobs.find(job => job.job_id === detailJobId) || null : null

  return (
    <div className="h-full overflow-y-auto px-3 pb-4">
      {description ? (
        <p className="px-1 pt-2 pb-3 text-[0.8125rem] leading-5 text-(--ui-text-secondary)">{description}</p>
      ) : null}
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 px-1 py-2 text-[0.8125rem]">
        <dt className="text-(--ui-text-tertiary)">Profile</dt>
        <dd className="truncate font-mono text-xs leading-5">{bot.name}</dd>
        <dt className="text-(--ui-text-tertiary)">Runs on</dt>
        <dd className="truncate leading-5">{bot.connectionLabel || 'This device'}</dd>
      </dl>
      <div className="flex items-center justify-between px-1 pt-3 pb-1.5">
        <span className="text-[0.8125rem] font-semibold">Routines</span>
        <Button onClick={() => host.revealPane(`${ID}:routines`)} size="xs" variant="text">
          <Codicon name="add" />
          New
        </Button>
      </div>
      {isLoading && !view.all.length ? (
        <div className="flex justify-center py-4">
          <GlyphSpinner className="text-(--ui-text-tertiary)" spinner="breathe" />
        </div>
      ) : view.jobs.length ? (
        <div className="grid gap-1.5">
          {view.jobs.map(job => (
            <RoutineRow job={job} key={job.job_id} onOpen={opened => setDetailJobId(opened.job_id)} owner={bot} />
          ))}
        </div>
      ) : (
        <p className="px-1 py-2 text-xs text-(--ui-text-tertiary)">
          No routines yet. Scheduled jobs this bot runs on its own show up here.
        </p>
      )}
      <RoutineDetailDialog job={detailJob} onClose={() => setDetailJobId(null)} open={Boolean(detailJob)} />
    </div>
  )
}
