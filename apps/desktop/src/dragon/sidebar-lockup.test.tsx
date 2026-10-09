import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { Intro } from '@/components/chat/intro'
import { I18nProvider } from '@/i18n'

import { DRAGON_PRODUCT } from './brand'
import { DRAGON_PRODUCT_VERSION, dragonProductVersionLabel } from './product-version'
import { DRAGON_LOCKUP_HEIGHT, DRAGON_MARKETPLACE_ROW_HEIGHT, DRAGON_SIDEBAR_CHROME_HEIGHT, DRAGON_TABS_HEIGHT } from './sidebar-chrome'
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

  it('shows the Dragon product version beside the wordmark, never a backend runtime string', () => {
    render(
      <I18nProvider>
        <DragonSidebarLockup />
      </I18nProvider>
    )

    const label = screen.getByLabelText(`${DRAGON_PRODUCT.name} ${dragonProductVersionLabel()}`)
    expect(label.textContent).toBe(dragonProductVersionLabel(DRAGON_PRODUCT_VERSION))
    expect(label.textContent).not.toMatch(/0\.21\./)
    expect(label.compareDocumentPosition(screen.getByText(DRAGON_PRODUCT.wordmark)) & Node.DOCUMENT_POSITION_PRECEDING).toBeTruthy()

    expect(DRAGON_SIDEBAR_CHROME_HEIGHT).toBe(DRAGON_LOCKUP_HEIGHT + DRAGON_MARKETPLACE_ROW_HEIGHT + DRAGON_TABS_HEIGHT)
    expect(document.querySelector('div[data-dragon-lockup]')?.className).toContain('flex-col')
  })
})
