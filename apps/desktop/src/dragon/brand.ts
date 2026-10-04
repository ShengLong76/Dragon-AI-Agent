/** User-facing Dragon AI Claude names. The agent framework underneath is never named in the UI. */
export const DRAGON_PRODUCT = {
  name: 'Dragon AI Claude',
  wordmark: 'Dragon AI',
  edition: 'Claude',
  agentNoun: 'Dragon AI'
} as const

/** Fired when the user presses Begin on the model-confirm screen; Bot Mode answers by opening the Bots tab. */
export const DRAGON_ONBOARDING_BEGIN_EVENT = 'dragon:onboarding-begin'

export const DRAGON_GROK_PITCH = 'Sign in with SuperGrok or X Premium+ — Grok 4.7 with duplex voice, no API key'
