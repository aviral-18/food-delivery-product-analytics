import { cn } from '@/lib/utils'

export interface BarRow {
  label: string
  value: number
  display?: string
  tone?: string // css color for the bar
}

/** A ranked horizontal bar list — labels left, proportional bars + values. */
export function BarList({ rows, color = 'var(--chart-1)', max }: { rows: BarRow[]; color?: string; max?: number }) {
  const top = max ?? Math.max(1, ...rows.map((r) => r.value))
  return (
    <div className="flex flex-col gap-2">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-3">
          <div className="w-32 shrink-0 truncate text-[13px] text-ink-2" title={r.label}>
            {r.label}
          </div>
          <div className="relative h-6 flex-1 overflow-hidden rounded bg-surface-2">
            <div
              className={cn('absolute inset-y-0 left-0 rounded')}
              style={{ width: `${(r.value / top) * 100}%`, background: r.tone ?? color, opacity: 0.85 }}
            />
          </div>
          <div className="w-24 shrink-0 text-right text-[13px] font-medium tabnum text-ink">
            {r.display ?? r.value.toLocaleString('en-IN')}
          </div>
        </div>
      ))}
    </div>
  )
}
