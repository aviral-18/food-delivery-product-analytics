import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export interface Stat {
  label: string
  value: ReactNode
  hint?: string
  tone?: 'default' | 'good' | 'warning' | 'critical'
}

const TONE: Record<string, string> = {
  default: 'text-ink',
  good: 'text-[var(--good)]',
  warning: 'text-[var(--warning)]',
  critical: 'text-[var(--critical)]',
}

export function StatTiles({ stats, cols = 4 }: { stats: Stat[]; cols?: number }) {
  return (
    <div className={cn('grid gap-3', `grid-cols-2 md:grid-cols-${cols}`)}>
      {stats.map((s) => (
        <div key={s.label} className="rounded-[var(--radius-md)] border border-border bg-surface p-3.5">
          <div className="text-[12px] font-medium text-ink-2">{s.label}</div>
          <div className={cn('mt-1 text-[20px] font-semibold tracking-tight tabnum', TONE[s.tone ?? 'default'])}>
            {s.value}
          </div>
          {s.hint && <div className="mt-0.5 text-[11px] text-muted">{s.hint}</div>}
        </div>
      ))}
    </div>
  )
}
