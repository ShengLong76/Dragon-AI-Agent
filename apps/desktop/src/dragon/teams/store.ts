import { atom } from 'nanostores'

export const $teamsMarketplaceOpen = atom(false)

export function openTeamsMarketplace(): void {
  $teamsMarketplaceOpen.set(true)
}

export function closeTeamsMarketplace(): void {
  $teamsMarketplaceOpen.set(false)
}
