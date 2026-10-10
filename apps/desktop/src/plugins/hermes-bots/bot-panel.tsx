/**
 * The right-sidebar Bot panel: one bot's identity card with Details | Library |
 * Computer | Routines tabs. A single click on a roster row (or a pinned tile)
 * selects that bot and updates this pane immediately, keeping the current tab.
 * Double-click opens the Computer tab — the bot's VM desktop. Routines is the
 * cron list. Computer is the live VM desktop (RFB), with an honest status
 * when the guest is missing or the runtime has no display service.
 */

import { atom, Button, cn, Codicon, GlyphSpinner, host, PanelEmpty, useI18n, useQuery, useValue } from '@hermes/plugin-sdk'
import { useState } from 'react'

import { avatarColor, botAppearance, BotFace } from './avatar'
import {
  $lastJobs,
  CreateRoutineDialog,
  RoutineDetailDialog,
  routineFilterHint,
  RoutineRow,
  selectRoutineJobs,
  useRoutines
} from './cron'
import { $botMeta, $lastRoster, botSelectionKey } from './data'
import { useBots } from './i18n'
import { botRole, displayName } from './labels'
import { botRosterMeta, requestForBot } from './routing'
import { BotScreenPane } from './screen-pane'
import { ID } from './shared'
import { HubSkillsSection } from './skills-hub'
import { botSoulQueryKey, SoulEditorDialog } from './soul-editor-dialog'
import type { RosterRow } from './types'

export type BotPanelTab = 'computer' | 'details' | 'library' | 'routines'

export const BOT_PANEL_PANE_ID = `${ID}:bot-panel`

export const $botPanel = atom<{ key: string; tab: BotPanelTab } | null>(null)

export function openBotPanel(bot: RosterRow, tab: BotPanelTab = 'computer') {
  $botPanel.set({ key: botSelectionKey(bot), tab })
  host.revealPane(BOT_PANEL_PANE_ID)
}

/** Select this bot in the right pane without forcing the Computer tab. */
export function selectBotInPanel(bot: RosterRow) {
  const current = $botPanel.get()
  $botPanel.set({ key: botSelectionKey(bot), tab: current?.tab ?? 'computer' })
  host.revealPane(BOT_PANEL_PANE_ID)
}

/** Open this bot's Routines tab — the only cron / scheduled-jobs surface. */
export function openBotRoutines(bot: RosterRow) {
  openBotPanel(bot, 'routines')
}

const TABS: { id: BotPanelTab; label: string }[] = [
  { id: 'details', label: 'Details' },
  { id: 'library', label: 'Library' },
  { id: 'computer', label: 'Computer' },
  { id: 'routines', label: 'Routines' }
]

export function BotPanelPane() {
  const panel = useValue($botPanel)
  const roster = useValue($lastRoster)
  const allMeta = useValue($botMeta)
  const bot = panel ? roster.find(row => botSelectionKey(row) === panel.key) : null

  if (!panel || !bot) {
    return (
      <PanelEmpty
        description="Click a bot in the Bots tab to open its details, library, computer, and routines here. Double-click to jump to its computer."
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
      <div className="mx-3 flex flex-wrap gap-1 rounded-2xl bg-(--ui-bg-tertiary)/60 p-1" role="tablist">
        {TABS.map(tab => (
          <button
            aria-selected={panel.tab === tab.id}
            className={cn(
              'min-w-0 flex-1 rounded-full px-2 py-1.5 text-[0.75rem] font-medium transition-colors',
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
        {
          {
            computer: <BotScreenPane bot={bot} key={botSelectionKey(bot)} />,
            details: (
              <BotDetails
                bot={bot}
                description={meta?.description || bot.description || ''}
                key={botSelectionKey(bot)}
              />
            ),
            library: (
              <div className="h-full overflow-y-auto px-3 py-2">
                <HubSkillsSection bot={bot} />
              </div>
            ),
            routines: <BotRoutines bot={bot} />
          }[panel.tab]
        }
      </div>
    </div>
  )
}

function BotDetails({ bot, description }: { bot: RosterRow; description: string }) {
  const b = useBots()

  const { data: soul, isLoading: soulLoading } = useQuery({
    queryKey: botSoulQueryKey(bot),
    queryFn: async () => {
      const res = (await requestForBot(bot, 'profiles.describe', { name: bot.name })) as { soul?: string }

      return res.soul || ''
    }
  })

  const [editing, setEditing] = useState(false)
  const content = soul || ''

  return (
    <div className="h-full overflow-y-auto px-3 pb-4">
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 px-1 py-2 text-[0.8125rem]">
        <dt className="text-(--ui-text-tertiary)">Profile</dt>
        <dd className="truncate font-mono text-xs leading-5">{bot.name}</dd>
        <dt className="text-(--ui-text-tertiary)">Runs on</dt>
        <dd className="truncate leading-5">{bot.connectionLabel || 'This device'}</dd>
        <dt className="text-(--ui-text-tertiary)">Description</dt>
        <dd className="leading-5 text-(--ui-text-secondary)">{description || '—'}</dd>
      </dl>
      <section
        className="group cursor-text px-1 pt-3"
        data-slot="soul-preview"
        onDoubleClick={() => !soulLoading && setEditing(true)}
      >
        <div className="flex items-baseline justify-between gap-2 pb-1.5">
          <div className="text-[0.8125rem] font-semibold">SOUL.md</div>
          <span className="text-[0.65rem] text-(--ui-text-quaternary) opacity-0 transition-opacity group-hover:opacity-100">
            {b.soulEditor.hint}
          </span>
        </div>
        {soulLoading ? (
          <div className="flex justify-center py-4">
            <GlyphSpinner className="text-(--ui-text-tertiary)" spinner="breathe" />
          </div>
        ) : (
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md border border-(--ui-stroke-secondary) bg-(--ui-bg-tertiary)/40 px-2.5 py-2 font-mono text-[0.75rem] leading-5 text-(--ui-text-secondary) transition-colors group-hover:border-(--ui-stroke-primary)">
            {content}
          </pre>
        )}
      </section>
      <SoulEditorDialog bot={bot} initialContent={content} onClose={() => setEditing(false)} open={editing} />
    </div>
  )
}

function BotRoutines({ bot }: { bot: RosterRow }) {
  const { data, error, isLoading, refetch } = useRoutines(bot)
  const { t } = useI18n()
  const b = useBots()
  const [detailJobId, setDetailJobId] = useState<null | string>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const view = selectRoutineJobs(data, error, $lastJobs.get(), bot.name)
  const detailJob = detailJobId ? view.jobs.find(job => job.job_id === detailJobId) || null : null
  const filterHint = routineFilterHint(view.all, view.jobs)

  if (view.live) {
    $lastJobs.set(view.live)
  }

  const openCreate = () => setCreateOpen(true)

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-end px-3 pt-2 pb-1">
        <Button onClick={openCreate} size="xs">
          <Codicon name="add" />
          {t.cron.newCron}
        </Button>
      </div>
      {isLoading && !view.all.length ? (
        <div className="flex flex-1 items-center justify-center">
          <GlyphSpinner className="text-(--ui-text-tertiary)" spinner="breathe" />
        </div>
      ) : error && !view.all.length ? (
        <PanelEmpty
          action={
            <Button onClick={() => void refetch()} size="sm" variant="secondary">
              {t.common.retry}
            </Button>
          }
          description={b.cron.readFailure}
          icon="warning"
          title={t.cron.failedLoad}
        />
      ) : view.jobs.length ? (
        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
          <div className="grid gap-1.5">
            {view.jobs.map(job => (
              <RoutineRow job={job} key={job.job_id} onOpen={opened => setDetailJobId(opened.job_id)} owner={bot} />
            ))}
          </div>
        </div>
      ) : (
        <PanelEmpty
          action={
            <Button onClick={openCreate} size="sm">
              {t.cron.newCron}
            </Button>
          }
          description={filterHint || t.cron.emptyDescNew}
          icon="watch"
          title={t.cron.emptyTitleNew}
        />
      )}
      <RoutineDetailDialog job={detailJob} onClose={() => setDetailJobId(null)} open={Boolean(detailJob)} />
      <CreateRoutineDialog bot={bot} onClose={() => setCreateOpen(false)} open={createOpen} />
    </div>
  )
}
