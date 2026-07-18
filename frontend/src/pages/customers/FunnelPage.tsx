import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { InsightsPanel } from '@/components/InsightsPanel'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatNumber } from '@/lib/utils'
import { seriesColor } from '@/lib/palette'

interface Stage {
  stage: string
  customers: number
  pct_of_top: number
  step_conversion_pct: number
  drop_off_pct: number
}

export function FunnelPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<{ stages: Stage[] }>('funnel', '/customers/funnel')
  if (isLoading) return <LoadingState label="Building journey funnel…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data || !data.stages.length) return <EmptyState />

  const top = data.stages[0].customers || 1

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
      <Card className="xl:col-span-2">
        <CardHeader>
          <CardTitle>Signup → loyalty funnel</CardTitle>
          <span className="text-[12px] text-ink-2">Where customers drop off on the path from signup to a repeat, retained user.</span>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 py-2">
            {data.stages.map((st, i) => {
              const width = Math.max(6, (st.customers / top) * 100)
              return (
                <div key={st.stage}>
                  <div className="mb-1 flex items-baseline justify-between text-[13px]">
                    <span className="font-medium text-ink">{st.stage}</span>
                    <span className="tabnum text-ink-2">
                      {formatNumber(st.customers)} · {st.pct_of_top.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="h-9 flex-1">
                      <div
                        className="flex h-full items-center rounded-md px-3 text-[12px] font-medium text-white transition-all"
                        style={{ width: `${width}%`, background: seriesColor(i), minWidth: 60 }}
                      >
                        {st.customers.toLocaleString('en-IN')}
                      </div>
                    </div>
                    {i > 0 && (
                      <div className="w-28 shrink-0 text-right text-[12px]">
                        <span className={st.step_conversion_pct >= 60 ? 'text-[var(--good)]' : 'text-[var(--warning)]'}>
                          {st.step_conversion_pct.toFixed(0)}% kept
                        </span>
                        <div className="text-[11px] text-muted">-{st.drop_off_pct.toFixed(0)}% drop</div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
      <InsightsPanel page="retention" title="Funnel Insights" />
    </div>
  )
}
