import {
  Sparkles, TrendingUp, AlertTriangle, Search, ShieldAlert, Lightbulb, FlaskConical, type LucideIcon,
} from 'lucide-react'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/misc'
import type { Insight } from '@/types'
import { cn } from '@/lib/utils'

const TYPE_META: Record<string, { icon: LucideIcon; label: string }> = {
  summary: { icon: Sparkles, label: 'Summary' },
  trend: { icon: TrendingUp, label: 'Trend' },
  anomaly: { icon: AlertTriangle, label: 'Anomaly' },
  root_cause: { icon: Search, label: 'Root cause' },
  risk: { icon: ShieldAlert, label: 'Risk' },
  opportunity: { icon: Lightbulb, label: 'Opportunity' },
  recommendation: { icon: Lightbulb, label: 'Recommendation' },
  ab_test: { icon: FlaskConical, label: 'A/B test' },
}

const SEVERITY_ACCENT: Record<string, string> = {
  positive: 'var(--good)',
  low: 'var(--chart-1)',
  medium: 'var(--warning)',
  high: 'var(--critical)',
}

export function InsightsPanel({ page, title = 'AI Product Insights' }: { page: string; title?: string }) {
  const { data, isLoading } = useAnalytics<{ insights: Insight[] }>(`insights-${page}`, '/insights', { page })

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        {isLoading &&
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-20 w-full" />)}
        {data?.insights.map((ins, i) => {
          const meta = TYPE_META[ins.type] ?? TYPE_META.summary
          const accent = SEVERITY_ACCENT[ins.severity] ?? 'var(--chart-1)'
          const Icon = meta.icon
          return (
            <div
              key={i}
              className="rounded-[var(--radius-md)] border border-border bg-surface-2 p-3"
              style={{ borderLeft: `3px solid ${accent}` }}
            >
              <div className="mb-1 flex items-center gap-2">
                <Icon className="h-3.5 w-3.5" style={{ color: accent }} />
                <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: accent }}>
                  {meta.label}
                </span>
              </div>
              <p className={cn('text-[13px] font-semibold leading-snug text-ink')}>{ins.title}</p>
              <p className="mt-1 text-[12px] leading-relaxed text-ink-2">{ins.detail}</p>
            </div>
          )
        })}
        {!isLoading && (!data || data.insights.length === 0) && (
          <p className="py-6 text-center text-[13px] text-muted">No insights for the current filters.</p>
        )}
      </CardContent>
    </Card>
  )
}
