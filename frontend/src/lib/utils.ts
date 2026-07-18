import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** Tailwind-aware className combiner. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Indian-style compact currency: ₹12.3L, ₹4.5Cr. */
export function formatCurrency(value: number | null | undefined, compact = true): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (compact) {
    if (abs >= 1e7) return `${sign}₹${(abs / 1e7).toFixed(2)}Cr`
    if (abs >= 1e5) return `${sign}₹${(abs / 1e5).toFixed(2)}L`
    if (abs >= 1e3) return `${sign}₹${(abs / 1e3).toFixed(1)}K`
  }
  return `${sign}₹${abs.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

/** Compact number: 12.3K, 4.5L, 2.1Cr. */
export function formatNumber(value: number | null | undefined, compact = true): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (compact) {
    if (abs >= 1e7) return `${sign}${(abs / 1e7).toFixed(2)}Cr`
    if (abs >= 1e5) return `${sign}${(abs / 1e5).toFixed(2)}L`
    if (abs >= 1e3) return `${sign}${(abs / 1e3).toFixed(1)}K`
  }
  return `${sign}${abs.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
}

/** A fraction (0.293) -> "29.3%". */
export function formatPercent(fraction: number | null | undefined, digits = 1): string {
  if (fraction === null || fraction === undefined || Number.isNaN(fraction)) return '—'
  return `${(fraction * 100).toFixed(digits)}%`
}

/** An already-percentage value (29.3) -> "29.3%". */
export function formatPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${value.toFixed(digits)}%`
}

/** Format a value by a semantic type used across KPI cards. */
export function formatByType(value: number | null | undefined, type: string): string {
  switch (type) {
    case 'currency':
      return formatCurrency(value)
    case 'percent':
      return formatPercent(value)
    case 'minutes':
      return value === null || value === undefined ? '—' : `${value.toFixed(1)} min`
    case 'number':
    default:
      return formatNumber(value)
  }
}

export function formatMonth(iso: string): string {
  // "2025-03" or "2025-03-01" -> "Mar '25"
  const [y, m] = iso.split('-')
  const months = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
  return `${months[parseInt(m, 10)]} '${y.slice(2)}`
}

export const CITY_TIER_LABEL: Record<number, string> = { 1: 'Tier 1', 2: 'Tier 2', 3: 'Tier 3' }
