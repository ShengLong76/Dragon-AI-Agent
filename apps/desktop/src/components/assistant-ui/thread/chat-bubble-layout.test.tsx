import { type ThreadMessage } from '@assistant-ui/react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { stubThreadEnvironment, stubThreadViewportSize, ThreadRuntime, userMessage } from '../test-utils'

import { hasChatBubbleClipGuard, isChatBubbleHug } from './chat-bubble'

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

function isFlexOrGrid(className: string): boolean {
  return /(?:^|\s)(?:flex|inline-flex|grid|inline-grid)(?:\s|$)/.test(className)
}

describe('chat bubble layout', () => {
  it('guards the hug cluster against column overflow; the timestamp rides that cluster', async () => {
    render(
      <ThreadRuntime
        messages={[
          userMessage('user-1', 'what kind of a search did you do? https://example.com/very/long/path/that/must/wrap'),
          assistantMessage('Got it.')
        ]}
      >
        <Thread />
      </ThreadRuntime>
    )

    const userRoot = document.querySelector('[data-slot="aui_user-message-root"]')
    const userCluster = document.querySelector('[data-slot="aui_user-bubble-cluster"]')
    const userBubble = await screen.findByRole('button', { name: 'Edit message' })
    const assistantBubble = document.querySelector('[data-slot="aui_assistant-message-content"]')

    expect(userRoot).toBeTruthy()
    expect(userCluster).toBeTruthy()
    expect(assistantBubble).toBeTruthy()

    expect(hasChatBubbleClipGuard(userCluster!.className)).toBe(true)
    expect(isChatBubbleHug(userCluster!.className)).toBe(true)
    expect(userCluster!.className).not.toMatch(/(?:^|\s)w-full(?:\s|$)/)

    expect(hasChatBubbleClipGuard(userBubble.className)).toBe(true)
    expect(isChatBubbleHug(userBubble.className)).toBe(true)
    expect(userBubble.className).not.toMatch(/\bw-max\b/)

    for (const ancestor of [userRoot!, ...ancestorsUntil(userCluster!, userRoot!)]) {
      if (isFlexOrGrid(ancestor.className)) {
        expect(ancestor.className, ancestor.className).toMatch(/\bmin-w-0\b/)
      }
    }

    expect(userCluster!.contains(userBubble)).toBe(true)
    expect(userCluster!.className).toMatch(/\brelative\b/)
    const hoverStamp = [...userCluster!.querySelectorAll('[class*="absolute"]')].find(node => node.querySelector('time'))
    expect(hoverStamp).toBeTruthy()
    expect(hoverStamp!.querySelector('time')).toBeTruthy()

    expect(hasChatBubbleClipGuard(assistantBubble!.className)).toBe(true)
    expect(isChatBubbleHug(assistantBubble!.className)).toBe(true)
    expect(assistantBubble!.className).not.toMatch(/\bw-max\b/)
  })
})
