import { describe, expect, it } from 'vitest'

import {
  CHAT_BUBBLE_MAX_COLUMN_PERCENT,
  CHAT_BUBBLE_MAX_WIDTH_REM,
  CHAT_BUBBLE_ROW_CLASS,
  CHAT_BUBBLE_WIDTH_CLASS,
  hasChatBubbleColumnCap
} from './chat-bubble'

/**
 * James's screenshot: a short user prompt wrapped onto three lines because
 * nested `w-fit` + percentage `max-width` collapsed the bubble to min-content
 * (the longest word). The contract:
 *
 * - The painted bubble hugs max-content so a short phrase stays on one line.
 * - Wrap only after a share of the conversation row (not full-bleed).
 * - That percentage resolves against a full-width row, never another hug box.
 */
describe('chat bubble width', () => {
  it('hugs short text and caps long text against the conversation row', () => {
    expect(CHAT_BUBBLE_WIDTH_CLASS).toMatch(/\bw-max\b/)
    expect(CHAT_BUBBLE_WIDTH_CLASS).not.toMatch(/\bw-fit\b/)
    expect(CHAT_BUBBLE_MAX_COLUMN_PERCENT).toBeGreaterThanOrEqual(70)
    expect(CHAT_BUBBLE_MAX_COLUMN_PERCENT).toBeLessThan(100)
    expect(CHAT_BUBBLE_MAX_WIDTH_REM).toBeGreaterThanOrEqual(28)
    expect(hasChatBubbleColumnCap(CHAT_BUBBLE_WIDTH_CLASS)).toBe(true)
    expect(hasChatBubbleColumnCap(CHAT_BUBBLE_ROW_CLASS)).toBe(false)
  })

  it('gives the percentage cap a definite full-width containing block', () => {
    expect(CHAT_BUBBLE_ROW_CLASS).toMatch(/\bw-full\b/)
    expect(CHAT_BUBBLE_ROW_CLASS).not.toMatch(/\b(w-fit|w-max)\b/)
  })
})
