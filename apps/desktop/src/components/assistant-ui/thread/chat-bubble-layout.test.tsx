import { type ThreadMessage } from '@assistant-ui/react'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { stubThreadEnvironment, stubThreadViewportSize, ThreadRuntime, userMessage } from '../test-utils'

import { hasChatBubbleColumnCap, isChatBubbleHug } from './chat-bubble'

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
  it('caps the hug cluster once against the row; the timestamp rides that cluster', async () => {
    render(
      <ThreadRuntime messages={[userMessage('user-1', 'what kind of a search did you do?'), assistantMessage('Got it.')]}>
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

    expect(hasChatBubbleColumnCap(userCluster!.className)).toBe(true)
    expect(isChatBubbleHug(userCluster!.className)).toBe(true)
    expect(userCluster!.className).not.toMatch(/\bw-full\b/)

    expect(isChatBubbleHug(userBubble.className)).toBe(true)
    expect(userBubble.className).not.toMatch(/\bw-max\b/)
    expect(hasChatBubbleColumnCap(userBubble.className)).toBe(false)

    for (const ancestor of ancestorsUntil(userCluster!, userRoot!)) {
      expect(hasChatBubbleColumnCap(ancestor.className), ancestor.className).toBe(false)
    }

    expect(userCluster!.contains(userBubble)).toBe(true)
    expect(userCluster!.className).toMatch(/\brelative\b/)
    const hoverStamp = [...userCluster!.querySelectorAll('[class*="absolute"]')].find(node => node.querySelector('time'))
    expect(hoverStamp).toBeTruthy()
    expect(hoverStamp!.querySelector('time')).toBeTruthy()

    expect(isChatBubbleHug(assistantBubble!.className)).toBe(true)
    expect(assistantBubble!.className).toMatch(/\bmax-w-full\b/)
    expect(assistantBubble!.className).not.toMatch(/\bw-max\b/)
    expect(hasChatBubbleColumnCap(assistantBubble!.className)).toBe(false)
  })
})
