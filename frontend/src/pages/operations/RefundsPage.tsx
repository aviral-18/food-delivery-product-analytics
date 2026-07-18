import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { BarList } from '@/components/charts/BarList'
import { InsightsPanel } from '@/components/InsightsPanel'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatCurrency, formatNumber, formatPercent, formatPct } from '@/lib/utils'

interface RefundResponse {
  delivered_orders: number
  refunded_orders: number
  refund_rate: number
  refund_value: number
  refund_value_pct_of_gmv: number
  by_reason: { reason: string; orders: number; refund_value: number }[]
  refund_rate_late_vs_ontime: { is_late: number | boolean; delivered_orders: number; refund_rate: number }[]
}

export function RefundsPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<RefundResponse>('refunds', '/operations/refunds')
  if (isLoading) return <LoadingState label="Analysing refunds…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const ontime = data.refund_rate_late_vs_ontime.find((r) => !r.is_late)
  const late = data.refund_rate_late_vs_ontime.find((r) => !!r.is_late)

  return (
    <div className="space-y-5">
      <StatTiles
        stats={[
          { label: 'Refund rate', value: formatPercent(data.refund_rate), tone: 'warning' },
          { label: 'Refunded orders', value: formatNumber(data.refunded_orders) },
          { label: 'Refund value', value: formatCurrency(data.refund_value), tone: 'critical' },
          { label: '% of GMV', value: formatPct(data.refund_value_pct_of_gmv) },
        ]}
      />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card>
            <CardHeader><CardTitle>Refund reasons (by value)</CardTitle></CardHeader>
            <CardContent>
              <BarList
                color="var(--chart-8)"
                rows={data.by_reason.map((r) => ({ label: r.reason.replace(/_/g, ' '), value: r.refund_value, display: formatCurrency(r.refund_value) }))}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Late vs on-time refund rate</CardTitle>
              <span className="text-[12px] text-ink-2">Quantifies the SLA → refund link.</span>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-[var(--radius-md)] border border-border bg-surface-2 p-4 text-center">
                  <div className="text-[12px] text-ink-2">On-time orders</div>
                  <div className="mt-1 text-[26px] font-semibold tabnum text-[var(--good)]">{formatPercent(ontime?.refund_rate ?? 0)}</div>
                  <div className="text-[11px] text-muted">{formatNumber(ontime?.delivered_orders ?? 0)} orders</div>
                </div>
                <div className="rounded-[var(--radius-md)] border border-border bg-surface-2 p-4 text-center">
                  <div className="text-[12px] text-ink-2">Late orders</div>
                  <div className="mt-1 text-[26px] font-semibold tabnum text-[var(--critical)]">{formatPercent(late?.refund_rate ?? 0)}</div>
                  <div className="text-[11px] text-muted">{formatNumber(late?.delivered_orders ?? 0)} orders</div>
                </div>
              </div>
              {ontime && late && ontime.refund_rate > 0 && (
                <p className="mt-3 text-center text-[13px] text-ink-2">
                  Late deliveries refund <span className="font-semibold text-ink">{(late.refund_rate / ontime.refund_rate).toFixed(1)}×</span> more often.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
        <InsightsPanel page="refunds" title="Refund Insights" />
      </div>
    </div>
  )
}
