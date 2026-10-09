// Refuse leftover Hermes/Nous artwork in a Dragon desktop package.
// A previous generate can leave nous-girl.png / nous-logo*.png / hermes*.png
// in products/icons or source public/; those must never reach dist or asar.
import { existsSync, readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const FORBIDDEN_NAME = /nous|girl|hermes/i
const ASSET_EXT = /\.(png|jpe?g|gif|svg|ico|icns|webp|bmp|tiff?|avif)$/i

export function isForbiddenShippedAsset(relativePath) {
  const normalized = String(relativePath || '').replaceAll('\\', '/')
  const base = normalized.split('/').pop() || ''
  return ASSET_EXT.test(base) && FORBIDDEN_NAME.test(normalized)
}

export function listFilesRecursive(root) {
  if (!existsSync(root) || !statSync(root).isDirectory()) {
    return []
  }
  const files = []
  for (const entry of readdirSync(root, { withFileTypes: true })) {
    const full = join(root, entry.name)
    if (entry.isDirectory()) {
      files.push(...listFilesRecursive(full))
    } else if (entry.isFile()) {
      files.push(full)
    }
  }
  return files
}

export function findForbiddenShippedAssets(root) {
  const prefix = root.endsWith('/') || root.endsWith('\\') ? root : `${root}`
  return listFilesRecursive(root)
    .map(file => file.slice(prefix.length).replace(/^[\\/]/, '').replaceAll('\\', '/'))
    .filter(isForbiddenShippedAsset)
}

export function forbiddenShippedAssetsError(paths) {
  return (
    `forbidden Hermes/Nous artwork in the package: ${paths.join(', ')}. ` +
    `Dragon packages must not ship files matching nous|girl|hermes.`
  )
}
