import * as Popover from '@radix-ui/react-popover'
import { Check, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface Option {
  value: string | number
  label: string
}

export function MultiSelect({
  label,
  options,
  selected,
  onChange,
  width = 'w-44',
}: {
  label: string
  options: Option[]
  selected: (string | number)[]
  onChange: (values: (string | number)[]) => void
  width?: string
}) {
  const toggle = (v: string | number) => {
    onChange(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v])
  }
  const count = selected.length

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button
          className={cn(
            'flex h-8 items-center justify-between gap-2 rounded-md border border-border bg-surface px-2.5 text-[13px] text-ink-2 hover:bg-surface-2',
            width,
          )}
        >
          <span className="truncate">
            {label}
            {count > 0 && (
              <span className="ml-1 rounded bg-primary-soft px-1.5 py-0.5 text-[11px] font-semibold text-primary">
                {count}
              </span>
            )}
          </span>
          <ChevronDown className="h-3.5 w-3.5 shrink-0" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          sideOffset={6}
          align="start"
          className="z-50 max-h-72 w-56 overflow-y-auto rounded-lg border border-border bg-surface p-1 shadow-[var(--shadow)]"
        >
          {options.map((opt) => {
            const active = selected.includes(opt.value)
            return (
              <button
                key={String(opt.value)}
                onClick={() => toggle(opt.value)}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-[13px] text-ink hover:bg-surface-2"
              >
                <span
                  className={cn(
                    'flex h-4 w-4 shrink-0 items-center justify-center rounded border',
                    active ? 'border-primary bg-primary text-primary-fg' : 'border-border-strong',
                  )}
                >
                  {active && <Check className="h-3 w-3" />}
                </span>
                <span className="truncate">{opt.label}</span>
              </button>
            )
          })}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  )
}
