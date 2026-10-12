import { useStore } from '@nanostores/react'
import { memo, useMemo, useState } from 'react'

import { CatalogCard, catalogPaneHeight, catalogPaneOpen, ResizableCatalogPane } from '@/app/capabilities/catalog-browser'
import { useI18n } from '@/i18n'
import { type PluginCatalogBrowseEntry, searchPluginCatalog } from '@/lib/plugin-catalog'
import { $paneHeightOverride } from '@/store/panes'
import { openCatalogPluginInstall } from '@/store/plugin-catalog-install'

const CATALOG_PANE_ID = 'capabilities-plugin-catalog'
const BROWSE_LIMIT = 24
const SEARCH_LIMIT = 40

interface PluginCatalogBrowserProps {
  installedNames: ReadonlySet<string>
  profile: null | string
}

/** Native Dragon plugin catalog: local snapshot browse/search + install dialog. */
export const PluginCatalogBrowser = memo(function PluginCatalogBrowser({
  installedNames,
  profile
}: PluginCatalogBrowserProps) {
  const { t } = useI18n()
  const p = t.skills.plugins
  const h = t.skills.hub
  const heightOverride = useStore($paneHeightOverride(CATALOG_PANE_ID))
  const height = catalogPaneHeight(heightOverride)
  const open = catalogPaneOpen(height)
  const [query, setQuery] = useState('')

  const rows = useMemo(() => {
    const matches = searchPluginCatalog(query)

    return matches.slice(0, query.trim() ? SEARCH_LIMIT : BROWSE_LIMIT)
  }, [query])

  const addPlugin = (entry: PluginCatalogBrowseEntry) => {
    openCatalogPluginInstall(
      {
        name: entry.name,
        repo: entry.repo,
        sha: entry.sha,
        subdir: entry.subdir
      },
      profile
    )
  }

  return (
    <ResizableCatalogPane
      height={height}
      hint={p.catalogHint}
      onSearchChange={setQuery}
      open={open}
      paneId={CATALOG_PANE_ID}
      sashTestId="plugin-catalog-sash"
      searchLabel={h.search}
      searchPlaceholder={p.catalogTitle}
      searchValue={query}
      title={p.catalogTitle}
      toggleHide={p.catalogHide}
      toggleShow={p.catalogBrowse}
    >
      {rows.length === 0 ? (
        <p className="px-1 py-2 text-[0.7rem] text-(--ui-text-quaternary)">{h.noResults}</p>
      ) : (
        <div className="grid gap-1.5">
          {rows.map(entry => (
            <CatalogCard
              alreadyInstalled={installedNames.has(entry.name)}
              alreadyInstalledLabel={h.installed}
              description={entry.description}
              key={entry.name}
              name={entry.title || entry.name}
              onAdd={() => addPlugin(entry)}
            />
          ))}
        </div>
      )}
    </ResizableCatalogPane>
  )
})
