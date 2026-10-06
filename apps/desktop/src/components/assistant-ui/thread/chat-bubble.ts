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
 * Width: `w-max` (max-content) so a short phrase stays on one line; wrap
 * only after `min(80% of the conversation row, 36rem)`. The percentage MUST
 * resolve against a definite-width ancestor — the full-width transcript row
 * (`CHAT_BUBBLE_ROW_CLASS`). Nesting this cap inside another `w-fit` /
 * `w-max` box is cyclic: the used width collapses to min-content (longest
 * word) and a prompt like "what is hermes serv" wraps onto three lines.
 */

/** Share of the transcript row a bubble may occupy before wrapping. */
export const CHAT_BUBBLE_MAX_COLUMN_PERCENT = 80

/** Absolute wrap cap so ultrawide windows stay readable. */
export const CHAT_BUBBLE_MAX_WIDTH_REM = 36

/** Full-width alignment row. Gives the 80% cap a definite containing block. */
export const CHAT_BUBBLE_ROW_CLASS = 'w-full min-w-0 max-w-full'

/** Painted bubble: hug text, wrap at the conversation-row cap. */
export const CHAT_BUBBLE_WIDTH_CLASS =
  `w-max max-w-[min(${CHAT_BUBBLE_MAX_COLUMN_PERCENT}%,${CHAT_BUBBLE_MAX_WIDTH_REM}rem)]`

/** Visible Grok-style corner. Must not go through `--radius-*` / `--radius-scalar`. */
export const CHAT_BUBBLE_RADIUS_CLASS = 'rounded-[1.25rem]'

/** True when a class list applies the conversation-row percentage cap. */
export function hasChatBubbleColumnCap(className: string): boolean {
  return new RegExp(
    String.raw`max-w-\[min\(${CHAT_BUBBLE_MAX_COLUMN_PERCENT}%,${CHAT_BUBBLE_MAX_WIDTH_REM}rem\)\]`
  ).test(className)
}
