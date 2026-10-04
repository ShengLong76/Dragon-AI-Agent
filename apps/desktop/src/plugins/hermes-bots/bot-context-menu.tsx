/**
 * The bot context menu shared by the list row and the pinned tile.
 *
 * Pinned bots leave the list and live only as tiles, so this menu is the
 * only Edit / Unpin surface they have. Both actions follow the label the
 * user clicked: Edit always opens, Unpin always writes `pinned: false`.
 * Delete stays off the default profile.
 */

import {
  Codicon,
  ContextMenu,
  ContextMenuCheckboxItem,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger,
  host,
  queryClient,
  useI18n,
  useValue
} from '@hermes/plugin-sdk'
import type { ReactNode } from 'react'

import { openBotPanel } from './bot-panel'
import { saveSelectedRosterBot } from './bot-state'
import { ensureBotMetadata } from './canonical-chat'
import { $botMeta, $lastRoster, botSelectionKey, isDefaultBot, newBotChat, ROSTER_KEY, saveBotMeta } from './data'
import { botGroups } from './group-membership'
import { fallbackSelectionAfterHide, isBotHidden, isBotPinned } from './hidden-bots'
import { useBots } from './i18n'
import { displayName } from './labels'
import { duplicateBot } from './profile-ops'
import { botRecentSession, openBotRecentSession } from './recent-session'
import { openRosterBot } from './roster-actions'
import { botRosterMeta, botWorkspaceOwnerKey, setBotsWorkspaceOwner } from './routing'
import { openBotScreen } from './screen-open'
import type { RosterRow } from './types'
import { $botSections, botSectionId, moveBotsToSection } from './user-sections'

export interface BotContextMenuProps {
  bot: RosterRow
  children: ReactNode
  onDelete: (bot: RosterRow) => void
  onEdit: (bot: RosterRow) => void
  onGroup: (bot: RosterRow) => void
  onNewSection: (bot: RosterRow) => void
}

export function BotContextMenu({ bot, children, onDelete, onEdit, onGroup, onNewSection }: BotContextMenuProps) {
  const { t } = useI18n()
  const b = useBots()
  const allMeta = useValue($botMeta)
  const meta = botRosterMeta(bot, allMeta)
  const hidden = isBotHidden(bot, allMeta)
  const pinned = isBotPinned(bot, allMeta)
  const groups = botGroups(meta)
  const sections = useValue($botSections)
  const currentSectionId = botSectionId(bot, allMeta)

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onSelect={() => void openRosterBot(bot)}>{b.bot.openBotChat}</ContextMenuItem>
        <ContextMenuItem onSelect={() => openBotPanel(bot, 'computer')}>{b.screen.menu}</ContextMenuItem>
        <ContextMenuItem onSelect={() => openBotScreen(bot, meta)}>Open computer in a tab</ContextMenuItem>
        <ContextMenuCheckboxItem
          checked={Boolean(meta?.screenAutoOpen)}
          onSelect={() => {
            void ensureBotMetadata(bot)
              .then(current => {
                const next = !current.screenAutoOpen
                void saveBotMeta(bot, { screenAutoOpen: next })
                host.notify({
                  kind: 'info',
                  message: next
                    ? b.screen.autoOpenOnToast(displayName(bot, current))
                    : b.screen.autoOpenOffToast(displayName(bot, current))
                })
              })
              .catch(error => host.notifyError?.(error, b.bot.metadataLoadFailed))
          }}
        >
          {b.screen.autoOpenMenu}
        </ContextMenuCheckboxItem>
        <ContextMenuSeparator />
        <ContextMenuItem
          onSelect={() => {
            // Honor the label: Unpin writes false even when a hydrate returns
            // a row that omitted `pinned` (that used to flip the bot back on).
            const nextPinned = !pinned
            void ensureBotMetadata(bot)
              .then(current => {
                void saveBotMeta(bot, { pinned: nextPinned })
                host.notify({
                  kind: 'info',
                  message: nextPinned
                    ? b.bot.pinnedToast(displayName(bot, current))
                    : b.bot.unpinnedToast(displayName(bot, current))
                })
              })
              .catch(error => host.notifyError?.(error, b.bot.metadataLoadFailed))
          }}
        >
          {pinned ? b.bot.unpin : b.bot.pinToTop}
        </ContextMenuItem>
        <ContextMenuItem
          onSelect={() => {
            void ensureBotMetadata(bot)
              .then(current => {
                const nextHidden = Boolean(current.hidden)
                void saveBotMeta(bot, {
                  hidden: !nextHidden
                })

                if (!nextHidden) {
                  fallbackSelectionAfterHide(botSelectionKey(bot))
                }

                host.notify({
                  kind: 'info',
                  message: nextHidden
                    ? b.bot.unhiddenToast(displayName(bot, current))
                    : b.bot.hiddenToast(displayName(bot, current))
                })
              })
              .catch(error => host.notifyError?.(error, b.bot.metadataLoadFailed))
          }}
        >
          {hidden ? b.bot.unhide : b.bot.hide}
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem
          data-slot="bot_edit_menu"
          onSelect={() => {
            onEdit(bot)
            void ensureBotMetadata(bot).catch(() => undefined)
          }}
        >
          {b.bot.editMenu}
        </ContextMenuItem>
        <ContextMenuItem
          onSelect={() =>
            void ensureBotMetadata(bot)
              .then(() => onGroup(bot))
              .catch(error => host.notifyError?.(error, b.bot.groupsLoadFailed))
          }
        >
          {groups.length ? b.bot.groupsMenu(groups.join(', ')) : b.bot.manageGroups}
        </ContextMenuItem>
        <ContextMenuItem
          onSelect={() => {
            host.notify({
              kind: 'info',
              message: `Duplicating ${displayName(bot, meta)}…`
            })
            duplicateBot(bot, $lastRoster.get())
              .then(name => {
                queryClient.invalidateQueries({
                  queryKey: ROSTER_KEY
                })
                host.notify({
                  kind: 'success',
                  message: `Created ${name} — full copy of ${bot.name}`
                })
              })
              .catch(err => host.notifyError(err, b.bot.duplicateFailed))
          }}
        >
          {b.bot.duplicate}
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem
          onSelect={() => {
            saveSelectedRosterBot(bot)
            setBotsWorkspaceOwner(botWorkspaceOwnerKey(bot), bot)
            newBotChat(bot)
          }}
        >
          {b.bot.newChatWith}
        </ContextMenuItem>
        <ContextMenuItem disabled={!botRecentSession(bot)} onSelect={() => void openBotRecentSession(bot)}>
          Open recent session
        </ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuSub>
          <ContextMenuSubTrigger>{b.sections.moveTo}</ContextMenuSubTrigger>
          <ContextMenuSubContent>
            {sections.map(section => (
              <ContextMenuItem
                disabled={section.id === currentSectionId}
                key={section.id}
                onSelect={() => void moveBotsToSection([bot], section.id)}
              >
                <Codicon className="mr-1.5" name="folder" />
                {section.name}
              </ContextMenuItem>
            ))}
            {sections.length ? <ContextMenuSeparator /> : null}
            <ContextMenuItem onSelect={() => onNewSection(bot)}>
              <Codicon className="mr-1.5" name="new-folder" />
              {b.sections.newSectionEllipsis}
            </ContextMenuItem>
            {currentSectionId ? (
              <ContextMenuItem onSelect={() => void moveBotsToSection([bot], null)}>
                <Codicon className="mr-1.5" name="inbox" />
                {b.sections.removeFromSection}
              </ContextMenuItem>
            ) : null}
          </ContextMenuSubContent>
        </ContextMenuSub>
        {isDefaultBot(bot) ? null : <ContextMenuSeparator />}
        {isDefaultBot(bot) ? null : (
          <ContextMenuItem onSelect={() => onDelete(bot)} variant="destructive">
            {t.common.delete}
          </ContextMenuItem>
        )}
      </ContextMenuContent>
    </ContextMenu>
  )
}
