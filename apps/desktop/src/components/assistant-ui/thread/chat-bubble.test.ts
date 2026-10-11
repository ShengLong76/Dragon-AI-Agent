import { describe, expect, it } from 'vitest'

import {
  ASSISTANT_CHAT_BUBBLE_WIDTH_CLASS,
  CHAT_BUBBLE_CLIP_GUARD_CLASS,
  CHAT_BUBBLE_HUG_CLASS,
  CHAT_BUBBLE_ROW_CLASS,
  CHAT_BUBBLE_WIDTH_CLASS,
  hasChatBubbleClipGuard,
  isChatBubbleHug,
  measureChatBubbleOverflow,
  measureChatBubbleWidth
} from './chat-bubble'

/**
 * James: when side panes narrow the conversation column, bubbles must
 * resize with it. Nothing — short prompts, long prose, code, tables, tool
 * cards, long URLs — may be clipped or hidden. Shrink-wrap is allowed only
 * when it cannot overflow the column.
 */

const SHORT_USER = 'what kind of a search did you do?'
const SHORT_CONTENT_PX = 248
const LONG_CONTENT_PX = 2400
const LONG_URL_PX = 1800
const NARROW_COLUMNS = [200, 240, 280, 320, 360] as const
const WIDE_COLUMNS = [480, 640, 800, 1200] as const

describe('chat bubble clip guard', () => {
  it('ships a static min-w-0 / max-w-full / wrap-anywhere candidate', () => {
    expect(CHAT_BUBBLE_CLIP_GUARD_CLASS).not.toContain('${')
    expect(hasChatBubbleClipGuard(CHAT_BUBBLE_CLIP_GUARD_CLASS)).toBe(true)
    expect(hasChatBubbleClipGuard(CHAT_BUBBLE_WIDTH_CLASS)).toBe(true)
    expect(hasChatBubbleClipGuard(CHAT_BUBBLE_HUG_CLASS)).toBe(true)
    expect(hasChatBubbleClipGuard(ASSISTANT_CHAT_BUBBLE_WIDTH_CLASS)).toBe(true)
    expect(hasChatBubbleClipGuard(CHAT_BUBBLE_ROW_CLASS)).toBe(false)
  })

  it('hugs short text without taking the row or dropping the clip guard', () => {
    expect(isChatBubbleHug(CHAT_BUBBLE_WIDTH_CLASS)).toBe(true)
    expect(isChatBubbleHug(ASSISTANT_CHAT_BUBBLE_WIDTH_CLASS)).toBe(true)
    expect(isChatBubbleHug(CHAT_BUBBLE_ROW_CLASS)).toBe(false)
    expect(CHAT_BUBBLE_ROW_CLASS).toMatch(/\bmin-w-0\b/)
    expect(CHAT_BUBBLE_ROW_CLASS).toMatch(/\bmax-w-full\b/)
  })
})

describe('measureChatBubbleWidth', () => {
  it('keeps a short user prompt narrower than a wide column', () => {
    const width = measureChatBubbleWidth({
      role: 'user',
      columnWidthPx: 800,
      contentWidthPx: SHORT_CONTENT_PX
    })

    expect(width).toBe(SHORT_CONTENT_PX)
    expect(width).toBeLessThan(800)
    expect(SHORT_USER.length).toBeGreaterThan(10)
  })

  it.each([...NARROW_COLUMNS, ...WIDE_COLUMNS])(
    'never exceeds a %i px column for short, long, or unbreakable content',
    columnWidthPx => {
      for (const contentWidthPx of [80, SHORT_CONTENT_PX, LONG_CONTENT_PX, LONG_URL_PX]) {
        for (const role of ['user', 'assistant'] as const) {
          const width = measureChatBubbleWidth({ role, columnWidthPx, contentWidthPx })

          expect(width).toBeLessThanOrEqual(columnWidthPx)
          expect(width).toBe(Math.min(contentWidthPx, columnWidthPx))
          expect(measureChatBubbleOverflow({ role, columnWidthPx, contentWidthPx })).toBe(0)
        }
      }
    }
  )

  it('reflows a long bubble all the way down when a side pane steals width', () => {
    const wide = measureChatBubbleWidth({
      role: 'user',
      columnWidthPx: 800,
      contentWidthPx: LONG_CONTENT_PX
    })
    const mid = measureChatBubbleWidth({
      role: 'user',
      columnWidthPx: 400,
      contentWidthPx: LONG_CONTENT_PX
    })
    const narrow = measureChatBubbleWidth({
      role: 'user',
      columnWidthPx: 200,
      contentWidthPx: LONG_CONTENT_PX
    })

    expect(wide).toBe(800)
    expect(mid).toBe(400)
    expect(narrow).toBe(200)
    expect(wide).toBeGreaterThan(mid)
    expect(mid).toBeGreaterThan(narrow)
  })

  it('does not clip a long URL in a 240px column', () => {
    expect(
      measureChatBubbleOverflow({
        role: 'user',
        columnWidthPx: 240,
        contentWidthPx: LONG_URL_PX
      })
    ).toBe(0)
    expect(
      measureChatBubbleWidth({
        role: 'assistant',
        columnWidthPx: 240,
        contentWidthPx: LONG_URL_PX
      })
    ).toBe(240)
  })
})
