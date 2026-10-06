import { IconBuildingStore, IconChevronRight } from '@tabler/icons-react'
import { useLayoutEffect } from 'react'

import { DRAGON_LOGO_SRC } from '@/components/brand-mark'
import { cn } from '@/lib/utils'

import { DRAGON_PRODUCT } from './brand'
import { DRAGON_LOCKUP_HEIGHT, DRAGON_MARKETPLACE_ROW_HEIGHT, DRAGON_TITLEBAR_CLUSTER_NUDGE } from './sidebar-chrome'
import { openTeamsMarketplace } from './teams/store'

/**
 * The Dragon lockup band at the top of the left sidebar, plus the Teams
 * Marketplace entry directly beneath it. The titlebar's hide-sidebar toggle
 * stays in its fixed left cluster; the lockup starts at
 * `--panel-titlebar-left` (the measured right edge of that cluster + gap), so
 * the toggle always sits to the LEFT of the logo and never over it.
 */
export function DragonSidebarLockup() {
  useLayoutEffect(() => {
    const root = document.documentElement
    root.style.setProperty('--dragon-titlebar-cluster-nudge', `${DRAGON_TITLEBAR_CLUSTER_NUDGE}px`)
    root.dataset.dragonLockup = ''

    return () => {
      delete root.dataset.dragonLockup
    }
  }, [])

  return (
    <div aria-label={DRAGON_PRODUCT.name} className="absolute inset-x-0 top-0 flex flex-col" data-dragon-lockup="">
      <div
        className="flex min-w-0 items-center gap-2.5 pr-3 [-webkit-app-region:drag]"
        style={{ height: DRAGON_LOCKUP_HEIGHT, paddingLeft: 'var(--panel-titlebar-left, 3rem)' }}
      >
        <img
          alt=""
          className="dragon-lockup-mark size-[2.125rem] shrink-0 object-contain"
          draggable={false}
          src={DRAGON_LOGO_SRC}
        />
        <div className="min-w-0 leading-none">
          <div
            className="wordmark dragon-wordmark truncate text-[1.0625rem] text-foreground"
            data-dragon-wordmark=""
          >
            {DRAGON_PRODUCT.wordmark}
          </div>
          {DRAGON_PRODUCT.edition ? (
            <div className="mt-1 truncate text-[0.625rem] font-semibold uppercase tracking-[0.24em] text-(--ui-text-tertiary)">
              {DRAGON_PRODUCT.edition}
            </div>
          ) : null}
        </div>
      </div>
      <div className="flex items-center px-2.5" style={{ height: DRAGON_MARKETPLACE_ROW_HEIGHT }}>
        <TeamsMarketplaceButton />
      </div>
    </div>
  )
}

function TeamsMarketplaceButton({ className }: { className?: string }) {
  return (
    <button
      className={cn(
        'group flex h-9 w-full min-w-0 items-center gap-2.5 rounded-xl bg-(--ui-bg-quaternary) px-3 text-left text-[0.8125rem] font-medium text-foreground transition-colors [-webkit-app-region:no-drag] hover:bg-(--chrome-action-hover)',
        className
      )}
      data-dragon-teams-entry=""
      onClick={() => openTeamsMarketplace()}
      type="button"
    >
      <IconBuildingStore className="size-4 shrink-0 text-(--ui-text-secondary)" stroke={1.75} />
      <span className="min-w-0 flex-1 truncate">Teams Marketplace</span>
      <IconChevronRight
        className="size-3.5 shrink-0 text-(--ui-text-tertiary) transition-transform group-hover:translate-x-0.5"
        stroke={2}
      />
    </button>
  )
}
