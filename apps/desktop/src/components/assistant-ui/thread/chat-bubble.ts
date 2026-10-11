/**
 * Shared Grok-style chat bubble geometry and fills.
 *
 * User bubbles sit on the right, agent bubbles on the left. Both shrink to
 * their text instead of painting a full-bleed slab.
 *
 * Radius is a literal rem, not `rounded-xl`. `--radius-xl` is
 * `--radius-scalar * 1rem` (3.2px at the default 0.2 scalar, 9.6px under
 * Dragon's 0.6) so `rounded-xl` reads as square. 1.25rem (20px) is the Grok
 * Bot corner James approved.
 *
 * Fills are the two Grok graphite values, not theme mixes: the user token
 * used to ride `--ui-chat-bubble-background`, which dark-mixes `#2f2f2f`
 * 46% into `#161618` and lands on the same gray as `--dt-muted` (`#1b1b1b`).
 *
 * Width: `inline-flex` / `inline-block` + `w-fit` so a short phrase hugs on
 * one line. User bubbles wrap after `min(80% of the conversation row, 36rem)`.
 * Assistant bubbles may grow to the full column so code/tables stay readable.
 *
 * The percentage MUST resolve against a definite-width ancestor — the
 * full-width transcript row (`CHAT_BUBBLE_ROW_CLASS`) — and the class string
 * MUST be a static Tailwind candidate. Interpolating `min(${percent}%,…)`
 * hides the utility from the scanner, so the cap never ships and `w-max` on
 * a block-level flex item with `w-full` children takes the whole column.
 *
 * Nesting the percentage cap inside another hug box is cyclic (the #57
 * wrap-too-early bug). Put the cap on the outermost hug box that is a child
 * of the row; inner painted surfaces use `CHAT_BUBBLE_HUG_CLASS`.
 */

/** Share of the transcript row a user bubble may occupy before wrapping. */
export const CHAT_BUBBLE_MAX_COLUMN_PERCENT = 80

/** Absolute wrap cap so ultrawide windows stay readable. */
export const CHAT_BUBBLE_MAX_WIDTH_REM = 36

/** Full-width alignment row. Gives the 80% cap a definite containing block. */
export const CHAT_BUBBLE_ROW_CLASS = 'w-full min-w-0 max-w-full'

/** Shrink-wrap only. Safe to nest; no percentage cap. */
export const CHAT_BUBBLE_HUG_CLASS = 'inline-flex w-fit'

/**
 * User/cluster: hug text, wrap at 80% of a definite-width row (or 36rem).
 * Static string — Tailwind v4 will not emit an interpolated arbitrary value.
 */
export const CHAT_BUBBLE_WIDTH_CLASS = 'inline-flex w-fit max-w-[min(80%,36rem)]'

/** Assistant: hug short replies; grow for code/tables up to the column. */
export const ASSISTANT_CHAT_BUBBLE_WIDTH_CLASS = 'inline-block w-fit max-w-full'

/** Visible Grok-style corner. Must not go through `--radius-*` / `--radius-scalar`. */
export const CHAT_BUBBLE_RADIUS_CLASS = 'rounded-[1.25rem]'

const COLUMN_CAP_RE = new RegExp(
  String.raw`max-w-\[min\(${CHAT_BUBBLE_MAX_COLUMN_PERCENT}%,${CHAT_BUBBLE_MAX_WIDTH_REM}rem\)\]`
)

/** True when a class list applies the conversation-row percentage cap. */
export function hasChatBubbleColumnCap(className: string): boolean {
  return COLUMN_CAP_RE.test(className)
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
 * content's max-content width (unwrapped text, a code card, a table).
 *
 * User bubbles never occupy the full column unless the text itself is that
 * wide: they cap at `min(80% of the column, 36rem)`. Assistant bubbles may
 * grow to the full column so code blocks and tables stay readable, but a
 * short reply still reports only its content width.
 *
 * CSS is the runtime; this is the numeric twin the width tests measure
 * (jsdom has no layout). Keep it in lockstep with the static class strings.
 */
export function measureChatBubbleWidth({
  role,
  columnWidthPx,
  contentWidthPx,
  remPx = 16
}: {
  role: ChatBubbleRole
  columnWidthPx: number
  contentWidthPx: number
  remPx?: number
}): number {
  if (columnWidthPx <= 0) {
    return 0
  }

  const cap =
    role === 'assistant'
      ? columnWidthPx
      : Math.min((columnWidthPx * CHAT_BUBBLE_MAX_COLUMN_PERCENT) / 100, CHAT_BUBBLE_MAX_WIDTH_REM * remPx)

  return Math.min(Math.max(contentWidthPx, 0), cap)
}
