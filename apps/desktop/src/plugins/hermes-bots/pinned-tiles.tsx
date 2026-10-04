/**
 * The pinned-bot strip at the top of the Bots tab: big circular avatars with
 * the bot's name and role badge, like a messenger's pinned conversations.
 * A click opens the bot's chat; a double-click opens its computer in the
 * right-side Bot panel.
 */

import { cn, useValue } from '@hermes/plugin-sdk'

import { avatarColor, botAppearance, BotFace } from './avatar'
import { openBotPanel } from './bot-panel'
import { $selectedRosterKey } from './bot-state'
import { $botMeta, botRosterKey } from './data'
import { botRole, displayName } from './labels'
import { openRosterBot } from './roster-actions'
import { botRosterMeta } from './routing'
import type { RosterRow } from './types'

export function PinnedBotTiles({ bots }: { bots: RosterRow[] }) {
  const allMeta = useValue($botMeta)
  const selectedKey = useValue($selectedRosterKey)

  if (!bots.length) {
    return null
  }

  return (
    <div
      className="grid grid-cols-[repeat(auto-fill,minmax(5.75rem,1fr))] gap-1 px-2 pt-1 pb-2"
      data-slot="dragon-pinned-bots"
    >
      {bots.map(bot => {
        const meta = botRosterMeta(bot, allMeta)
        const { shape, color, image } = botAppearance(bot.name, meta)
        const key = botRosterKey(bot)
        const name = displayName(bot, meta)

        return (
          <button
            aria-label={name}
            className={cn(
              'group grid min-w-0 justify-items-center gap-1.5 rounded-2xl px-1.5 pt-3 pb-2.5 text-center transition-colors',
              'hover:bg-(--chrome-action-hover)',
              selectedKey === key && 'bg-(--ui-row-active-background)'
            )}
            data-roster-key={key}
            key={key}
            onClick={() => void openRosterBot(bot)}
            onDoubleClick={() => openBotPanel(bot, 'computer')}
            type="button"
          >
            <span className="grid size-16 place-items-center overflow-hidden rounded-full bg-(--ui-bg-tertiary) ring-1 ring-(--ui-stroke-tertiary)">
              <BotFace color={avatarColor(color, bot.name)} image={image} name={bot.name} shape={shape} size={48} />
            </span>
            <span className="w-full truncate text-[0.8125rem] font-semibold leading-tight">{name}</span>
            <span className="max-w-full truncate rounded-full bg-(--ui-bg-tertiary) px-2 py-px text-[0.6875rem] font-medium text-(--ui-text-tertiary)">
              {botRole(bot, meta)}
            </span>
          </button>
        )
      })}
    </div>
  )
}
