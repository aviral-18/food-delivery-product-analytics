/**
 * Chart palette helpers.
 *
 * Colors are referenced as CSS variables so Recharts marks re-theme with the
 * app (SVG fill/stroke accept `var(--chart-N)`). The order is the validated,
 * colorblind-safe categorical order from the data-viz reference.
 */
export const SERIES = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
  'var(--chart-6)',
  'var(--chart-7)',
  'var(--chart-8)',
] as const

export const STATUS = {
  good: 'var(--good)',
  warning: 'var(--warning)',
  serious: 'var(--serious)',
  critical: 'var(--critical)',
} as const

export const CHROME = {
  grid: 'var(--grid)',
  ink: 'var(--ink)',
  ink2: 'var(--ink-2)',
  muted: 'var(--muted)',
  primary: 'var(--primary)',
  surface: 'var(--surface)',
} as const

/** Series color by index, cycling only as a last resort (avoid >8 series). */
export function seriesColor(i: number): string {
  return SERIES[i % SERIES.length]
}

/** Map a health/score 0-100 to a status color. */
export function scoreColor(score: number): string {
  if (score >= 75) return STATUS.good
  if (score >= 55) return 'var(--chart-1)'
  if (score >= 40) return STATUS.warning
  if (score >= 25) return STATUS.serious
  return STATUS.critical
}
