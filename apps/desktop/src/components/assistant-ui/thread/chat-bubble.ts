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
 */

/** Width of both voices: hug the text, never wider than 80% or 36rem. */
export const CHAT_BUBBLE_WIDTH_CLASS = 'w-fit max-w-[min(80%,36rem)]'

/** Visible Grok-style corner. Must not go through `--radius-*` / `--radius-scalar`. */
export const CHAT_BUBBLE_RADIUS_CLASS = 'rounded-[1.25rem]'
