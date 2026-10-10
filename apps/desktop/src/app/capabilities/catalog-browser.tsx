import { type PointerEvent as ReactPointerEvent, type ReactNode, useRef, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ADD_TO_AGENT_LABEL } from '@/lib/dragon-hub-catalog'
import { Loader2 } from '@/lib/icons'
import { cn } from '@/lib/utils'
import { setPaneHeightOverride } from '@/store/panes'

const DEFAULT_PX = 380
const MIN_PX = 120
const MAX_VH = 0.75
const COLLAPSED_PX = 4
const LIST_RESERVED_PX = 176

export function catalogPaneOpen(height: number): boolean {
  return height > COLLAPSED_PX
}

export function catalogPaneHeight(override: null | number | undefined): number {
  return override ?? DEFAULT_PX
}

interface CatalogCardProps {
  alreadyInstalled?: boolean
  alreadyInstalledLabel: string
  busy?: boolean
  description?: string
  disabled?: boolean
  name: string
  onAdd: () => void
}

export function CatalogCard({
  alreadyInstalled = false,
  alreadyInstalledLabel,
  busy = false,
  description,
  disabled = false,
  name,
  onAdd
}: CatalogCardProps) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-(--ui-stroke-secondary) px-2.5 py-2">
      <div className="min-w-0 flex-1">
        <div className="truncate text-[0.75rem] font-medium text-(--ui-text-primary)">{name}</div>
        {description ? (
          <div className="line-clamp-2 text-[0.65rem] leading-4 text-(--ui-text-quaternary)">{description}</div>
        ) : null}
      </div>
      {alreadyInstalled ? (
        <span className="shrink-0 text-[0.65rem] text-(--ui-text-tertiary)">{alreadyInstalledLabel}</span>
      ) : (
        <Button
          aria-label={`${ADD_TO_AGENT_LABEL}: ${name}`}
          className="shrink-0 px-2 font-semibold"
          disabled={disabled || busy}
          onClick={onAdd}
          size="xs"
          variant="secondary"
        >
          {busy && <Loader2 className="size-3 animate-spin" />}
          {ADD_TO_AGENT_LABEL}
        </Button>
      )}
    </div>
  )
}

interface ResizableCatalogPaneProps {
  children: ReactNode
  headerActions?: ReactNode
  height: number
  hidden?: boolean
  hint: string
  onSearchChange?: (value: string) => void
  onSearchSubmit?: () => void
  open: boolean
  paneId: string
  sashTestId?: string
  searchLabel: string
  searchPlaceholder: string
  searchValue?: string
  searching?: boolean
  title: string
  toggleHide: string
  toggleShow: string
}

/** Shared Skills/Plugins catalog chrome: sash, Dragon title, search, viewport. */
export function ResizableCatalogPane({
  children,
  headerActions,
  height,
  hidden = false,
  hint,
  onSearchChange,
  onSearchSubmit,
  open,
  paneId,
  sashTestId,
  searchLabel,
  searchPlaceholder,
  searchValue = '',
  searching = false,
  title,
  toggleHide,
  toggleShow
}: ResizableCatalogPaneProps) {
  const [dragging, setDragging] = useState(false)
  const sectionRef = useRef<HTMLElement>(null)

  const startDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) {
      return
    }

    event.preventDefault()
    const startY = event.clientY
    const startHeight = height
    const column = sectionRef.current?.parentElement
    const columnMax = column ? column.clientHeight - LIST_RESERVED_PX : Number.POSITIVE_INFINITY
    const max = Math.max(MIN_PX, Math.round(Math.min(window.innerHeight * MAX_VH, columnMax)))
    setDragging(true)

    const onMove = (move: globalThis.PointerEvent) => {
      setPaneHeightOverride(
        paneId,
        Math.round(Math.min(max, Math.max(MIN_PX, startHeight + (startY - move.clientY))))
      )
    }

    const onUp = () => {
      window.removeEventListener('pointermove', onMove)
      setDragging(false)
    }

    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp, { once: true })
  }

  return (
    <section
      className={cn(
        'relative flex min-h-9 flex-col overflow-hidden border-t border-(--ui-stroke-secondary)',
        hidden && 'hidden'
      )}
      data-catalog-pane={paneId}
      ref={sectionRef}
    >
      <div
        className="group/hubsash absolute inset-x-0 top-0 z-10 h-1 -translate-y-1/2 cursor-row-resize"
        data-testid={sashTestId}
        onDoubleClick={() => setPaneHeightOverride(paneId, undefined)}
        onPointerDown={startDrag}
      >
        <div
          className={cn(
            'absolute inset-x-0 top-1/2 h-px -translate-y-1/2 transition-colors',
            dragging ? 'bg-(--ui-stroke-secondary)' : 'group-hover/hubsash:bg-(--ui-stroke-secondary)'
          )}
        />
      </div>
      <div className="flex shrink-0 items-center justify-between px-3 py-1.5">
        <span className="text-[0.7rem] font-medium text-(--ui-text-tertiary)">{title}</span>
        <div className="flex items-center gap-1">
          {headerActions}
          <Button onClick={() => setPaneHeightOverride(paneId, open ? 0 : undefined)} size="xs" variant="text">
            {open ? toggleHide : toggleShow}
          </Button>
        </div>
      </div>
      {open && (
        <div className="flex min-h-0 flex-col gap-1.5 px-3 pb-2">
          {onSearchChange && (
            <div className="flex shrink-0 gap-1.5">
              <Input
                aria-label={searchLabel}
                className="h-7 flex-1 text-xs"
                onChange={event => onSearchChange(event.target.value)}
                onKeyDown={event => {
                  if (event.nativeEvent?.isComposing || event.keyCode === 229) {
                    return
                  }

                  if (event.key === 'Enter' && onSearchSubmit) {
                    event.preventDefault()
                    onSearchSubmit()
                  }
                }}
                placeholder={searchPlaceholder}
                value={searchValue}
              />
              {onSearchSubmit && (
                <Button disabled={searching || !searchValue.trim()} onClick={onSearchSubmit} size="sm" variant="secondary">
                  {searching ? <Loader2 className="size-3 animate-spin" /> : searchLabel}
                </Button>
              )}
            </div>
          )}
          <div
            className="min-h-0 overflow-y-auto overscroll-contain"
            style={{ flex: `0 1 ${height}px` }}
          >
            {children}
          </div>
          <p className="shrink-0 px-1 text-[0.65rem] leading-4 text-(--ui-text-quaternary)">{hint}</p>
        </div>
      )}
    </section>
  )
}
