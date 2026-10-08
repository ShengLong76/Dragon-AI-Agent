interface DarwinFeed {
  /** Feed directory key under the public bucket, no trailing slash.
   *  e.g. "releases/darwin/stable" | "releases/darwin/light/canary" */
  directory: string
  /** Validated slug; existence is resolved through R2. */
  channel: string
  /** electron-updater manifest filename. e.g. "stable-mac.yml" */
  fileName: string
  /** Legacy nonstable feeds admit prereleases. */
  allowPrerelease: boolean
}

interface ProductFeed {
  productName: string
  productRepository: string
  upstreamRepository: string
  githubReleasesHtml: string
  publicAssetsBase: string | null
  protectedPaths: string[]
}

/**
 * Feed layout contract shared by the desktop runtime and the release
 * pipeline. `light` selects the Light-variant feed directory.
 * The generic-provider feed URL is PUBLIC_URL + '/' + directory + '/' + fileName.
 */
declare function darwinFeed(channel: string, light?: boolean): DarwinFeed

/** Validate and canonicalize the public updater feed base URL. */
declare function feedBaseUrl(raw: string | undefined): string | undefined

/** Packaged feed origin: only the product-feed CDN, never a leftover Hermes R2 URL. */
declare function packagedFeedBaseUrl(envUrl?: string): string | undefined

declare function productRepository(): string
declare function upstreamRepository(): string
declare function isProductRepository(repository?: string | null): boolean
declare function isUpstreamRepository(repository?: string | null): boolean

declare const contract: {
  darwinFeed: typeof darwinFeed
  feedBaseUrl: typeof feedBaseUrl
  packagedFeedBaseUrl: typeof packagedFeedBaseUrl
  productFeed: ProductFeed
  productRepository: typeof productRepository
  upstreamRepository: typeof upstreamRepository
  isProductRepository: typeof isProductRepository
  isUpstreamRepository: typeof isUpstreamRepository
}
export = contract
