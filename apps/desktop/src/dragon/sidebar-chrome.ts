import { TITLEBAR_HEIGHT } from '@/app/shell/titlebar'

/** Logo band. Taller than the titlebar so the 34px mark never crowds the toggle. */
export const DRAGON_LOCKUP_HEIGHT = TITLEBAR_HEIGHT + 12
/** Teams Marketplace entry, directly under the lockup. */
export const DRAGON_MARKETPLACE_ROW_HEIGHT = 44
/** Sessions | Bots strip. */
export const DRAGON_TABS_HEIGHT = 36

/** Total reserved chrome above the left sidebar's body. Tabs never share the logo band. */
export const DRAGON_SIDEBAR_CHROME_HEIGHT = DRAGON_LOCKUP_HEIGHT + DRAGON_MARKETPLACE_ROW_HEIGHT + DRAGON_TABS_HEIGHT

/** Vertical offset that centers the titlebar's left cluster on the logo band. */
export const DRAGON_TITLEBAR_CLUSTER_NUDGE = (DRAGON_LOCKUP_HEIGHT - TITLEBAR_HEIGHT) / 2
