import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Intro } from '@/components/chat/intro'
import { I18nProvider } from '@/i18n'

import { DRAGON_PRODUCT } from './brand'
import { DragonSidebarLockup } from './sidebar-lockup'

afterEach(() => {
  cleanup()
})

describe('empty-state lockup face', () => {
  it('uses the title-bar product-name face, not a separate lockup font', () => {
    render(
      <I18nProvider>
        <Intro />
        <DragonSidebarLockup />
      </I18nProvider>
    )

    const headerTitle = screen.getByText(DRAGON_PRODUCT.wordmark)
    const emptyLockup = document.querySelector('[data-slot="aui_intro"] .wordmark')

    expect(headerTitle.classList.contains('dragon-wordmark')).toBe(true)
    expect(headerTitle.classList.contains('wordmark')).toBe(false)
    expect(emptyLockup?.classList.contains('dragon-wordmark')).toBe(true)
    expect(emptyLockup?.textContent).toContain('DRAGON AI')
    expect(screen.getByRole('button', { name: 'Teams Marketplace' })).toBeTruthy()
  })
})
