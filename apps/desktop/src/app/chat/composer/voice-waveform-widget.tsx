import { useEffect, useRef, useState } from 'react'

import { Codicon } from '@/components/ui/codicon'
import { useI18n } from '@/i18n'
import { triggerHaptic } from '@/lib/haptics'
import { cn } from '@/lib/utils'

import type { ConversationStatus } from './hooks/use-voice-conversation'

const BAR_COUNT = 24

interface VoiceWaveformWidgetProps {
  level: number
  muted: boolean
  status: ConversationStatus
  onEnd: () => void
  onToggleMute: () => void
}

function useAnimatedBars(level: number, status: ConversationStatus, muted: boolean): number[] {
  const [bars, setBars] = useState<number[]>(() => Array.from({ length: BAR_COUNT }, () => 0.12))
  const levelRef = useRef(level)
  levelRef.current = level

  useEffect(() => {
    let raf = 0
    const start = performance.now()

    const tick = (now: number) => {
      const t = (now - start) / 1000
      const live = status === 'listening' && !muted ? Math.min(1, levelRef.current * 1.6) : 0
      const speaking = status === 'speaking'
      const busy = status === 'thinking' || status === 'transcribing'

      setBars(
        Array.from({ length: BAR_COUNT }, (_, i) => {
          const center = 1 - Math.abs(i - (BAR_COUNT - 1) / 2) / (BAR_COUNT / 2)
          const wobble = 0.5 + 0.5 * Math.sin(t * 7 + i * 0.75) * Math.cos(t * 3.1 + i * 0.4)

          if (speaking) {
            return 0.2 + 0.75 * center * (0.35 + 0.65 * wobble)
          }

          if (busy) {
            const sweep = 0.5 + 0.5 * Math.sin(t * 4 - i * 0.45)

            return 0.12 + 0.28 * sweep * center
          }

          return 0.1 + live * center * (0.45 + 0.55 * wobble)
        })
      )

      raf = requestAnimationFrame(tick)
    }

    raf = requestAnimationFrame(tick)

    return () => cancelAnimationFrame(raf)
  }, [muted, status])

  return bars
}

export function VoiceWaveformWidget({ level, muted, status, onEnd, onToggleMute }: VoiceWaveformWidgetProps) {
  const { t } = useI18n()
  const c = t.composer
  const bars = useAnimatedBars(level, status, muted)

  const label =
    status === 'speaking'
      ? c.speaking
      : status === 'transcribing'
        ? c.transcribing
        : status === 'thinking'
          ? c.thinking
          : muted
            ? c.muted
            : c.listening

  return (
    <div
      className="pointer-events-auto absolute bottom-[calc(100%+0.75rem)] left-1/2 z-20 flex -translate-x-1/2 items-center gap-3 rounded-full border border-white/8 bg-[#1c1c1e]/95 py-2 pl-2 pr-2 text-white shadow-[0_12px_40px_rgba(0,0,0,0.55)] backdrop-blur-md"
      data-slot="voice-waveform-widget"
      role="group"
    >
      <button
        aria-label={muted ? c.unmuteMic : c.muteMic}
        aria-pressed={muted}
        className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-full transition-colors',
          muted ? 'bg-white/12 text-white/60' : 'bg-white/6 text-white hover:bg-white/12'
        )}
        onClick={() => {
          triggerHaptic('selection')
          onToggleMute()
        }}
        type="button"
      >
        <Codicon name={muted ? 'mic-off' : 'mic'} size="1rem" />
      </button>

      <div aria-hidden="true" className="flex h-9 w-[9.5rem] items-center justify-between" data-slot="voice-waveform-bars">
        {bars.map((height, index) => (
          <span
            className={cn('w-[3px] rounded-full', muted ? 'bg-white/35' : 'bg-white')}
            key={index}
            style={{ height: `${Math.round(height * 100)}%` }}
          />
        ))}
      </div>

      <span aria-hidden="true" className="min-w-[4.5rem] text-xs font-medium text-white/70">
        {label}
      </span>

      <button
        aria-label={c.endConversation}
        className="flex size-9 shrink-0 items-center justify-center rounded-full bg-white text-black transition-colors hover:bg-white/85"
        onClick={() => {
          triggerHaptic('close')
          onEnd()
        }}
        type="button"
      >
        <Codicon name="close" size="1rem" />
      </button>
    </div>
  )
}
