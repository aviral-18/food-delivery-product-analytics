import * as Popover from '@radix-ui/react-popover'
import { CalendarRange, RotateCcw, SlidersHorizontal, Check } from 'lucide-react'
import { useFilters } from '@/state/FiltersProvider'
import { MultiSelect } from '@/components/ui/multi-select'
import { cn } from '@/lib/utils'

const DATA_START = '2024-07-01'
const DATA_END = '2026-06-30'

const PRESETS: { label: string; start?: string; end?: string }[] = [
  { label: 'All time (24 months)', start: undefined, end: undefined },
  { label: 'Last 30 days', start: '2026-06-01', end: DATA_END },
  { label: 'Last 90 days', start: '2026-04-01', end: DATA_END },
  { label: 'Last 6 months', start: '2026-01-01', end: DATA_END },
  { label: 'Last 12 months', start: '2025-07-01', end: DATA_END },
  { label: 'Year 2025', start: '2025-01-01', end: '2025-12-31' },
]

function labelForDates(start?: string, end?: string): string {
  const match = PRESETS.find((p) => p.start === start && p.end === end)
  if (match) return match.label
  if (start || end) return `${start ?? DATA_START} → ${end ?? DATA_END}`
  return 'All time (24 months)'
}

export function FilterBar() {
  const { filters, patch, reset, activeCount, reference } = useFilters()

  const cityOptions = (reference?.cities ?? []).map((c) => ({ value: c.id, label: `${c.name} (T${c.tier})` }))
  const cuisineOptions = (reference?.cuisines ?? []).map((c) => ({ value: c.id, label: c.name }))
  const channelOptions = (reference?.filter_options.channels ?? []).map((c) => ({
    value: c,
    label: c.replace(/_/g, ' '),
  }))
  const dayPartOptions = (reference?.filter_options.day_parts ?? []).map((c) => ({
    value: c,
    label: c.replace(/_/g, ' '),
  }))

  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-border bg-surface/60 px-5 py-2.5">
      <div className="mr-1 flex items-center gap-1.5 text-[12px] font-medium text-muted">
        <SlidersHorizontal className="h-3.5 w-3.5" />
        Filters
      </div>

      {/* Date range presets */}
      <Popover.Root>
        <Popover.Trigger asChild>
          <button className="flex h-8 items-center gap-2 rounded-md border border-border bg-surface px-2.5 text-[13px] text-ink hover:bg-surface-2">
            <CalendarRange className="h-3.5 w-3.5 text-muted" />
            {labelForDates(filters.start_date, filters.end_date)}
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            sideOffset={6}
            align="start"
            className="z-50 w-52 rounded-lg border border-border bg-surface p-1 shadow-[var(--shadow)]"
          >
            {PRESETS.map((p) => {
              const active = filters.start_date === p.start && filters.end_date === p.end
              return (
                <button
                  key={p.label}
                  onClick={() => patch({ start_date: p.start, end_date: p.end })}
                  className="flex w-full items-center justify-between rounded-md px-2 py-1.5 text-left text-[13px] text-ink hover:bg-surface-2"
                >
                  {p.label}
                  {active && <Check className="h-3.5 w-3.5 text-primary" />}
                </button>
              )
            })}
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>

      <MultiSelect
        label="City"
        options={cityOptions}
        selected={filters.city_ids ?? []}
        onChange={(v) => patch({ city_ids: v as number[] })}
      />
      <MultiSelect
        label="Cuisine"
        options={cuisineOptions}
        selected={filters.cuisine_ids ?? []}
        onChange={(v) => patch({ cuisine_ids: v as number[] })}
      />
      <MultiSelect
        label="Channel"
        options={channelOptions}
        selected={filters.channels ?? []}
        onChange={(v) => patch({ channels: v as string[] })}
      />
      <MultiSelect
        label="Day part"
        options={dayPartOptions}
        selected={filters.day_parts ?? []}
        onChange={(v) => patch({ day_parts: v as string[] })}
      />

      {activeCount > 0 && (
        <button
          onClick={reset}
          className={cn(
            'flex h-8 items-center gap-1.5 rounded-md px-2.5 text-[13px] font-medium text-ink-2 hover:bg-surface-2 hover:text-ink',
          )}
        >
          <RotateCcw className="h-3.5 w-3.5" />
          Reset
        </button>
      )}
    </div>
  )
}
