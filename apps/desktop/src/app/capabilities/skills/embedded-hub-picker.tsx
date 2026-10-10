import { useStore } from '@nanostores/react'
import { memo, useEffect, useMemo, useState } from 'react'

import { CatalogCard, catalogPaneHeight, catalogPaneOpen, ResizableCatalogPane } from '@/app/capabilities/catalog-browser'
import { Button } from '@/components/ui/button'
import { getSkillHubSources, searchSkillsHub, type ProfileScope } from '@/hermes'
import { useI18n } from '@/i18n'
import {
  DRAGON_FEATURED_SKILLS,
  type HubCatalogSkill,
  hubSkillKey,
  matchesInstalled,
  mergeHubCatalogSkills
} from '@/lib/dragon-hub-catalog'
import { Loader2 } from '@/lib/icons'
import { useStoreSelector } from '@/lib/use-session-slice'
import {
  $hubActions,
  installHubSkill,
  notifyHubActionFailed,
  UPDATE_ALL_KEY,
  updateHubSkills
} from '@/store/hub-actions'
import { notify, notifyError } from '@/store/notifications'
import { $paneHeightOverride } from '@/store/panes'
import type { SkillHubResult } from '@/types/hermes'

const HUB_PANE_ID = 'capabilities-hub'

function profileName(scope?: ProfileScope): null | string {
  if (!scope) {
    return null
  }

  return typeof scope === 'string' ? scope : (scope.profile ?? null)
}

function asHubSkill(row: SkillHubResult): HubCatalogSkill {
  return {
    description: row.description || '',
    identifier: row.identifier || row.name,
    name: row.name || row.identifier,
    source: row.source
  }
}

interface EmbeddedHubPickerProps {
  /** Kept mounted but fully hidden (display:none) across tab switches. */
  hidden?: boolean
  /** Names of skills already installed in the scoped profile. */
  installedNames: ReadonlySet<string>
  /** Capabilities profile-scope override — installs land in THIS profile. */
  profile?: ProfileScope
}

/** Native Dragon Skills Hub: local featured catalog + registry search/install. */
export const EmbeddedHubPicker = memo(function EmbeddedHubPicker({
  hidden = false,
  installedNames,
  profile
}: EmbeddedHubPickerProps) {
  const { t } = useI18n()
  const h = t.skills.hub
  const updating = useStoreSelector($hubActions, actions => actions[UPDATE_ALL_KEY]?.running ?? false)
  const heightOverride = useStore($paneHeightOverride(HUB_PANE_ID))
  const height = catalogPaneHeight(heightOverride)
  const open = catalogPaneOpen(height)
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchRows, setSearchRows] = useState<HubCatalogSkill[] | null>(null)
  const [featured, setFeatured] = useState<HubCatalogSkill[]>(() => [...DRAGON_FEATURED_SKILLS])
  const [searchError, setSearchError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      return undefined
    }

    let cancelled = false

    void getSkillHubSources(profileName(profile))
      .then(response => {
        if (cancelled) {
          return
        }

        const extra = (response.featured ?? []).map(asHubSkill)
        setFeatured(mergeHubCatalogSkills(DRAGON_FEATURED_SKILLS, extra))
      })
      .catch(() => {
        if (!cancelled) {
          setFeatured([...DRAGON_FEATURED_SKILLS])
        }
      })

    return () => {
      cancelled = true
    }
  }, [open, profile])

  const rows = searchRows ?? featured

  const runningInstallKey = useStoreSelector($hubActions, actions =>
    Object.keys(actions)
      .filter(key => actions[key]?.running)
      .sort()
      .join('|')
  )
  const runningInstalls = useMemo(
    () => new Set(runningInstallKey.split('|').filter(Boolean)),
    [runningInstallKey]
  )

  const runSearch = () => {
    const q = query.trim()

    if (!q || searching) {
      return
    }

    setSearching(true)
    setSearchError(null)

    void searchSkillsHub(q, 'all', 40, profileName(profile))
      .then(response => {
        setSearchRows((response.results ?? []).map(asHubSkill))
      })
      .catch(() => {
        setSearchRows([])
        setSearchError(h.searchFailed)
      })
      .finally(() => setSearching(false))
  }

  const addSkill = (skill: HubCatalogSkill) => {
    const target = hubSkillKey(skill)
    const label = skill.name || target

    if (!target) {
      return
    }

    if (matchesInstalled(skill, installedNames)) {
      notify({ kind: 'success', title: h.alreadyInstalled(label), message: '' })

      return
    }

    notify({ kind: 'success', title: h.installStarted(label), message: h.actionLog })
    void installHubSkill(target, profile).catch(err => notifyHubActionFailed(err, h.actionFailed, label, profile))
  }

  const updateAll = () => {
    notify({ kind: 'success', title: h.updateStarted, message: h.actionLog })
    void updateHubSkills(profile).catch(err => notifyError(err, h.actionFailed))
  }

  return (
    <ResizableCatalogPane
      headerActions={
        <Button disabled={updating} onClick={updateAll} size="xs" variant="text">
          {updating && <Loader2 className="size-3 animate-spin" />}
          {updating ? h.updating : h.updateAll}
        </Button>
      }
      height={height}
      hidden={hidden}
      hint={h.pickerHint}
      onSearchChange={value => {
        setQuery(value)

        if (!value.trim()) {
          setSearchRows(null)
          setSearchError(null)
        }
      }}
      onSearchSubmit={runSearch}
      open={open}
      paneId={HUB_PANE_ID}
      searchLabel={h.search}
      searchPlaceholder={h.searchPlaceholder}
      searchValue={query}
      searching={searching}
      title={h.pickerTitle}
      toggleHide={h.pickerHide}
      toggleShow={h.pickerBrowse}
    >
      {searching ? (
        <p className="px-1 py-2 text-[0.7rem] text-(--ui-text-quaternary)">{h.searching}</p>
      ) : searchError ? (
        <p className="px-1 py-2 text-[0.7rem] text-(--ui-text-quaternary)">{searchError}</p>
      ) : rows.length === 0 ? (
        <p className="px-1 py-2 text-[0.7rem] text-(--ui-text-quaternary)">{h.noResults}</p>
      ) : (
        <div className="grid gap-1.5">
          {rows.map(skill => (
            <CatalogCard
              alreadyInstalled={matchesInstalled(skill, installedNames)}
              alreadyInstalledLabel={h.installed}
              busy={runningInstalls.has(hubSkillKey(skill)) || runningInstalls.has(skill.name)}
              description={skill.description}
              key={hubSkillKey(skill)}
              name={skill.name}
              onAdd={() => addSkill(skill)}
            />
          ))}
        </div>
      )}
    </ResizableCatalogPane>
  )
})
