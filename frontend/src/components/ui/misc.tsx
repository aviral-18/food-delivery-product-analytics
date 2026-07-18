import type { ComponentProps, ReactNode } from 'react'
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

export function Skeleton({ className, ...props }: ComponentProps<'div'>) {
  return <div className={cn('skeleton rounded-md', className)} {...props} />
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={cn('animate-spin text-muted', className)} />
}

export function Badge({
  children,
  tone = 'neutral',
  className,
}: {
  children: ReactNode
  tone?: 'neutral' | 'good' | 'warning' | 'serious' | 'critical' | 'primary'
  className?: string
}) {
  const tones: Record<string, string> = {
    neutral: 'bg-surface-2 text-ink-2 border-border',
    primary: 'bg-primary-soft text-primary border-transparent',
    good: 'bg-[color-mix(in_srgb,var(--good)_16%,transparent)] text-[var(--good)] border-transparent',
    warning: 'bg-[color-mix(in_srgb,var(--warning)_18%,transparent)] text-[var(--warning)] border-transparent',
    serious: 'bg-[color-mix(in_srgb,var(--serious)_18%,transparent)] text-[var(--serious)] border-transparent',
    critical: 'bg-[color-mix(in_srgb,var(--critical)_16%,transparent)] text-[var(--critical)] border-transparent',
  }
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium',
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted">
      <Spinner className="h-6 w-6" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function EmptyState({ title = 'No data', hint }: { title?: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <Inbox className="h-8 w-8 text-muted" />
      <p className="text-sm font-medium text-ink-2">{title}</p>
      {hint && <p className="max-w-sm text-[13px] text-muted">{hint}</p>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error?: unknown; onRetry?: () => void }) {
  const message =
    (error as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail ||
    (error as { message?: string })?.message ||
    'Something went wrong.'
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <AlertTriangle className="h-8 w-8 text-[var(--serious)]" />
      <p className="text-sm font-medium text-ink-2">Could not load this data</p>
      <p className="max-w-md text-[13px] text-muted">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-1 text-[13px] font-medium text-primary hover:underline">
          Try again
        </button>
      )}
    </div>
  )
}
