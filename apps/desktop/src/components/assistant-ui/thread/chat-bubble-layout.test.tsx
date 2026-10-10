import { type ThreadMessage } from '@assistant-ui/react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { stubThreadEnvironment, stubThreadViewportSize, ThreadRuntime, userMessage } from '../test-utils'

import { hasChatBubbleColumnCap } from './chat-bubble'

import { Thread } from '.'

stubThreadEnvironment()
stubThreadViewportSize()

afterEach(() => {
  cleanup()
})

function assistantMessage(text: string): ThreadMessage {
  return {
    id: 'assistant-1',
    role: 'assistant',
    content: [{ type: 'text', text }],
    status: { type: 'complete', reason: 'stop' },
    createdAt: new Date('2026-05-01T00:00:00.000Z'),
    metadata: { unstable_state: null, unstable_annotations: [], unstable_data: [], steps: [], custom: {} }
  } as ThreadMessage
}

function ancestorsUntil(node: Element, root: Element): Element[] {
  const chain: Element[] = []
  let current = node.parentElement

  while (current && current !== root) {
    chain.push(current)
    current = current.parentElement
  }

  return chain
}

describe('chat bubble layout', () => {
  it('applies the column cap once on the painted bubble, not on nested hug wrappers', async () => {
    render(
      <ThreadRuntime messages={[userMessage('user-1', 'what is dragon serve'), assistantMessage('a short reply')]}>
        <Thread />
      </ThreadRuntime>
    )

    const userRoot = document.querySelector('[data-slot="aui_user-message-root"]')
    const userBubble = await screen.findByRole('button', { name: 'Edit message' })
    const assistantBubble = document.querySelector('[data-slot="aui_assistant-message-content"]')

    expect(userRoot).toBeTruthy()
    expect(assistantBubble).toBeTruthy()

    expect(hasChatBubbleColumnCap(userBubble.className)).toBe(true)
    expect(userBubble.className).toMatch(/\bw-max\b/)

    for (const ancestor of ancestorsUntil(userBubble, userRoot!)) {
      expect(hasChatBubbleColumnCap(ancestor.className), ancestor.className).toBe(false)
    }

    expect(hasChatBubbleColumnCap(assistantBubble!.className)).toBe(true)
    expect(assistantBubble!.className).toMatch(/\bw-max\b/)
  })
})
