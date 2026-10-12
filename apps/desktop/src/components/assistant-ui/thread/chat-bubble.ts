/**
 * Shared Grok-style chat bubble geometry and fills.
 *
 * User bubbles sit on the right, agent bubbles on the left. Short phrases
 * may hug (`w-fit`); that is secondary. The load-bearing rule is James's
 * pane-resize contract: when the conversation column shrinks, every bubble
 * (user, assistant, code, table, tool card, long URL) must still fit. Text
 * is never clipped or hidden behind overflow. Horizontal scroll is allowed
 * only inside code blocks and tables.
 *
 * The clip guard is a static Tailwind candidate — `min-w-0 max-w-full
 * wrap-anywhere`. `min-w-0` lets flex/grid parents shrink below max-content
 * (the default `min-width: auto` is what clips when a side pane narrows the
 * column). `max-w-full` caps at the conversation row. `wrap-anywhere` breaks
 * long tokens. Do not interpolate these classes; Tailwind v4 will not emit
 * the utility and the bubble overflows the column.
 *
 * An 80% / 36rem wrap cap is intentionally gone. It wraps prose early, but
 * unbreakable chrome (fences, tables, URLs) wider than that cap overflows
 * and gets clipped by the transcript's `overflow-x-hidden`.
 */

/** Full-width alignment row. Definite containing block; can shrink. */
export const CHAT_BUBBLE_ROW_CLASS = 'w-full min-w-0 max-w-full'

/**
 * Never exceed the conversation column. Safe on the painted bubble and on
 * every flex/grid ancestor that sizes from content.
 */
export const CHAT_BUBBLE_CLIP_GUARD_CLASS = 'min-w-0 max-w-full wrap-anywhere'

/** Shrink-wrap short text without dropping the clip guard. */
export const CHAT_BUBBLE_HUG_CLASS = `inline-flex w-fit ${CHAT_BUBBLE_CLIP_GUARD_CLASS}`

/** User/cluster: hug when it fits; always bounded by the column. */
export const CHAT_BUBBLE_WIDTH_CLASS = CHAT_BUBBLE_HUG_CLASS

/** Assistant: same bound; `inline-block` so markdown/code/tables can grow. */
export const ASSISTANT_CHAT_BUBBLE_WIDTH_CLASS = `inline-block w-fit ${CHAT_BUBBLE_CLIP_GUARD_CLASS}`

/** Visible Grok-style corner. Must not go through `--radius-*` / `--radius-scalar`. */
export const CHAT_BUBBLE_RADIUS_CLASS = 'rounded-[1.25rem]'

/** True when a class list cannot overflow its containing block. */
export function hasChatBubbleClipGuard(className: string): boolean {
  return /\bmin-w-0\b/.test(className) && /\bmax-w-full\b/.test(className) && /\bwrap-anywhere\b/.test(className)
}

/** True when a class list shrink-wraps instead of taking the row's width. */
export function isChatBubbleHug(className: string): boolean {
  return (
    /\binline-(?:block|flex)\b/.test(className) &&
    /\bw-fit\b/.test(className) &&
    !/(?:^|\s)w-(?:full|max)(?:\s|$)/.test(className)
  )
}

export type ChatBubbleRole = 'assistant' | 'user'

/**
 * Used width of a painted bubble given the conversation column and the
 * content's preferred width (unwrapped text, a code card, a table, a URL).
 *
 * The used width is never larger than the column — that is the pane-resize
 * invariant. Short content may still hug. Unbreakable content that would
 * overflow is treated as wrapping (or scrolling inside a code/table card)
 * down to the column, not as spilling past it.
 *
 * CSS is the runtime; this is the numeric twin the width tests measure
 * (jsdom has no layout). Keep it in lockstep with the static class strings.
 */
export function measureChatBubbleWidth({
  columnWidthPx,
  contentWidthPx
}: {
  role?: ChatBubbleRole
  columnWidthPx: number
  contentWidthPx: number
}): number {
  if (columnWidthPx <= 0) {
    return 0
  }

  return Math.min(Math.max(contentWidthPx, 0), columnWidthPx)
}

/** Pixels of bubble that would paint past the conversation column. */
export function measureChatBubbleOverflow(args: {
  role?: ChatBubbleRole
  columnWidthPx: number
  contentWidthPx: number
}): number {
  const used = measureChatBubbleWidth(args)

  return Math.max(0, used - Math.max(args.columnWidthPx, 0))
}
