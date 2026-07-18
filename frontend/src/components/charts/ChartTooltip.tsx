import type { ReactNode } from 'react'

interface TooltipItem {
  name?: string
  value?: number | string
  color?: string
  dataKey?: string | number
}

/** Themed Recharts tooltip. `format` maps a datum value to a display string. */
export function ChartTooltip({
  active,
  payload,
  label,
  format,
  labelText,
}: {
  active?: boolean
  payload?: TooltipItem[]
  label?: string | number
  format?: (v: number, key: string) => string
  labelText?: (label: string | number) => string
}): ReactNode {
  if (!active || !payload || payload.length === 0) return null
  return (
    <div className="rounded-lg border border-border bg-[var(--glass)] px-3 py-2 text-[12px] shadow-[var(--shadow)] backdrop-blur-md">
      {label !== undefined && (
        <div className="mb-1 font-medium text-ink">{labelText ? labelText(label) : label}</div>
      )}
      <div className="flex flex-col gap-1">
        {payload.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ background: item.color }} />
            <span className="text-ink-2">{item.name}</span>
            <span className="ml-auto tabnum font-medium text-ink">
              {typeof item.value === 'number' && format
                ? format(item.value, String(item.dataKey))
                : item.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
