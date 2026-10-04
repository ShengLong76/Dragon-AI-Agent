/**
 * Shared Grok-style chat bubble geometry.
 *
 * User bubbles sit on the right, agent bubbles on the left. Both shrink to
 * their text instead of painting a full-bleed slab. Fills come from the
 * existing theme tokens (`--dt-user-bubble` / `--dt-assistant-bubble`); this
 * file does not invent colors.
 */

/** Width of both voices: hug the text, never wider than 80% or 36rem. */
export const CHAT_BUBBLE_WIDTH_CLASS = 'w-fit max-w-[min(80%,36rem)]'
