import { describe, expect, it } from 'vitest'

import {
  ASSISTANT_CHAT_BUBBLE_WIDTH_CLASS,
  CHAT_BUBBLE_HUG_CLASS,
  CHAT_BUBBLE_MAX_COLUMN_PERCENT,
  CHAT_BUBBLE_MAX_WIDTH_REM,
  CHAT_BUBBLE_ROW_CLASS,
  CHAT_BUBBLE_WIDTH_CLASS,
  hasChatBubbleColumnCap,
  isChatBubbleHug,
  measureChatBubbleWidth
} from './chat-bubble'

/**
 * James's screenshots:
 *
 * 1. A short prompt wrapped onto three lines because nested `w-fit` +
 *    percentage `max-width` collapsed to min-content (the longest word).
 * 2. After #57, every bubble stretched to the conversation column because
 *    `w-max` sat on a block-level flex item whose children were `w-full`,
 *    and the 80% cap was an interpolated class Tailwind never emitted.
 *
 * The contract:
 * - Short text hugs (used width ≈ content, not the column).
 * - Long user text wraps at 80% of the row / 36rem, then reflows when the
 *   column narrows (side panes).
 * - Assistant short replies hug; wide chrome (code/tables) may use the column.
 * - The percentage cap is a static Tailwind candidate on a hug box whose
 *   parent is the full-width row — never `w-full` / `w-max` on the paint.
 */

const SHORT_USER = 'what kind of a search did you do?'
const SHORT_CONTENT_PX = 248
const LONG_CONTENT_PX = 2400

describe('chat bubble width', () => {
  it('hugs with a static 80% / 36rem cap Tailwind can emit', () => {
    // Interpolating the arbitrary value hides it from the Tailwind scanner,
    // which is how #57 shipped a missing max-width and full-bleed bubbles.
    expect(CHAT_BUBBLE_WIDTH_CLASS).not.toContain('${')
    expect(CHAT_BUBBLE_WIDTH_CLASS).toContain(`${CHAT_BUBBLE_MAX_COLUMN_PERCENT}%`)
    expect(CHAT_BUBBLE_WIDTH_CLASS).toContain(`${CHAT_BUBBLE_MAX_WIDTH_REM}rem`)
    expect(CHAT_BUBBLE_MAX_COLUMN_PERCENT).toBeGreaterThanOrEqual(70)
    expect(CHAT_BUBBLE_MAX_COLUMN_PERCENT).toBeLessThan(100)
    expect(hasChatBubbleColumnCap(CHAT_BUBBLE_WIDTH_CLASS)).toBe(true)
    expect(hasChatBubbleColumnCap(CHAT_BUBBLE_ROW_CLASS)).toBe(false)
    expect(hasChatBubbleColumnCap(CHAT_BUBBLE_HUG_CLASS)).toBe(false)
    expect(isChatBubbleHug(CHAT_BUBBLE_WIDTH_CLASS)).toBe(true)
    expect(isChatBubbleHug(CHAT_BUBBLE_HUG_CLASS)).toBe(true)
    expect(isChatBubbleHug(CHAT_BUBBLE_ROW_CLASS)).toBe(false)
  })

  it('lets assistant chrome use the column without a user-style 80% cap', () => {
    expect(isChatBubbleHug(ASSISTANT_CHAT_BUBBLE_WIDTH_CLASS)).toBe(true)
    expect(hasChatBubbleColumnCap(ASSISTANT_CHAT_BUBBLE_WIDTH_CLASS)).toBe(false)
  })

  it('gives the percentage cap a definite full-width containing block', () => {
    expect(isChatBubbleHug(CHAT_BUBBLE_ROW_CLASS)).toBe(false)
    expect(hasChatBubbleColumnCap(CHAT_BUBBLE_ROW_CLASS)).toBe(false)
  })
})

describe('measureChatBubbleWidth', () => {
  it('keeps a short user prompt far narrower than a wide column', () => {
    const width = measureChatBubbleWidth({
      role: 'user',
      columnWidthPx: 800,
      contentWidthPx: SHORT_CONTENT_PX
    })

    expect(width).toBe(SHORT_CONTENT_PX)
    expect(width / 800).toBeLessThan(0.4)
    expect(SHORT_USER.length).toBeGreaterThan(10)
  })

  it('still hugs a short user prompt in a narrow column', () => {
    const width = measureChatBubbleWidth({
      role: 'user',
      columnWidthPx: 360,
      contentWidthPx: SHORT_CONTENT_PX
    })

    expect(width).toBe(SHORT_CONTENT_PX)
    expect(width).toBeLessThan(360 * (CHAT_BUBBLE_MAX_COLUMN_PERCENT / 100))
  })

  it('caps a long user message at 80% of a narrow column', () => {
    expect(
      measureChatBubbleWidth({
        role: 'user',
        columnWidthPx: 400,
        contentWidthPx: LONG_CONTENT_PX
      })
    ).toBe(320)
  })

  it('caps a long user message at 36rem on a wide column', () => {
    expect(
      measureChatBubbleWidth({
        role: 'user',
        columnWidthPx: 1200,
        contentWidthPx: LONG_CONTENT_PX
      })
    ).toBe(CHAT_BUBBLE_MAX_WIDTH_REM * 16)
  })

  it('reflows a long user bubble when the column shrinks (side panes)', () => {
    const wide = measureChatBubbleWidth({
      role: 'user',
      columnWidthPx: 800,
      contentWidthPx: LONG_CONTENT_PX
    })
    const narrow = measureChatBubbleWidth({
      role: 'user',
      columnWidthPx: 400,
      contentWidthPx: LONG_CONTENT_PX
    })

    expect(wide).toBeGreaterThan(narrow)
    expect(wide).toBeLessThan(800)
    expect(narrow).toBe(320)
  })

  it('hugs a short assistant reply instead of padding it to the column', () => {
    const width = measureChatBubbleWidth({
      role: 'assistant',
      columnWidthPx: 800,
      contentWidthPx: 96
    })

    expect(width).toBe(96)
    expect(width).toBeLessThan(800 * 0.3)
  })

  it('lets a wide assistant code/table card use the full column', () => {
    expect(
      measureChatBubbleWidth({
        role: 'assistant',
        columnWidthPx: 800,
        contentWidthPx: LONG_CONTENT_PX
      })
    ).toBe(800)

    expect(
      measureChatBubbleWidth({
        role: 'assistant',
        columnWidthPx: 360,
        contentWidthPx: LONG_CONTENT_PX
      })
    ).toBe(360)
  })
})
