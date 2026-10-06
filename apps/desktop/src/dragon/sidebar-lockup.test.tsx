import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Wordmark } from '@/components/chat/wordmark'

import { DRAGON_PRODUCT } from './brand'
import { DragonSidebarLockup } from './sidebar-lockup'

afterEach(() => {
  cleanup()
})

describe('DragonSidebarLockup', () => {
  it('uses the empty-state lockup lettering class for the title-bar product name', () => {
    const { container: intro } = render(<Wordmark text="DRAGON AI" />)
    const lockupClass = intro.querySelector('.wordmark')?.className ?? ''

    expect(lockupClass.split(/\s+/)).toContain('wordmark')

    cleanup()
    render(<DragonSidebarLockup />)

    const title = screen.getByText(DRAGON_PRODUCT.wordmark)
    expect(title.classList.contains('wordmark')).toBe(true)
    expect(screen.getByRole('button', { name: 'Teams Marketplace' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Teams Marketplace' }).compareDocumentPosition(title)).toBe(
      Node.DOCUMENT_POSITION_PRECEDING
    )
  })
})
