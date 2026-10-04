import { cn } from '@/lib/utils'

const assetPath = (path: string) => `${import.meta.env.BASE_URL}${path.replace(/^\/+/, '')}`

export const DRAGON_LOGO_SRC = assetPath('dragon-logo.png')

// Brand badge: the low-poly Dragon AI mark, rendered from the canonical
// artwork (branding/dragon-logo.png → public/dragon-logo.png) without any
// recoloring. Size via className (default size-14).
export function BrandMark({ className, ...props }: React.ComponentProps<'span'>) {
  return (
    <span className={cn('inline-flex size-14 shrink-0 items-center justify-center', className)} {...props}>
      <img alt="" className="size-full object-contain" draggable={false} src={DRAGON_LOGO_SRC} />
    </span>
  )
}
