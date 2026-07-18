import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { BarList } from '@/components/charts/BarList'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatCurrency, formatNumber } from '@/lib/utils'

interface Cell { dow: number; hour: number; orders: number; net_revenue: number }
interface PeakResponse {
  heatmap: Cell[]
  by_day_part: { day_part: string; orders: number; net_revenue: number; avg_margin: number }[]
  peak_slot: Cell | null
}

const DOW = [1, 2, 3, 4, 5, 6, 0]
const DOW_LABEL: Record<number, string> = { 0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat' }

export function PeakPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<PeakResponse>('peak', '/operations/peak-hours')
  if (isLoading) return <LoadingState label="Mapping peak-hour demand…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const lookup = new Map(data.heatmap.map((c) => [`${c.dow}-${c.hour}`, c]))
  const maxOrders = Math.max(1, ...data.heatmap.map((c) => c.orders))
  const hours = Array.from({ length: 24 }, (_, h) => h)
  const peak = data.peak_slot

  return (
    <div className="space-y-5">
      <StatTiles
        cols={3}
        stats={[
          { label: 'Peak slot', value: peak ? `${DOW_LABEL[peak.dow]} ${peak.hour}:00` : '—', hint: peak ? `${formatNumber(peak.orders)} orders` : undefined },
          { label: 'Busiest day-part', value: data.by_day_part[0]?.day_part ?? '—', tone: 'good' },
          { label: 'Total slots tracked', value: formatNumber(data.heatmap.length) },
        ]}
      />
      <Card>
        <CardHeader>
          <CardTitle>Demand heatmap — day of week × hour</CardTitle>
          <span className="text-[12px] text-ink-2">Darker = more orders. Use for staffing, surge and marketing timing.</span>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="border-separate border-spacing-[2px]">
              <thead>
                <tr>
                  <th className="w-10" />
                  {hours.map((h) => (
                    <th key={h} className="px-0.5 text-center text-[9px] font-medium text-muted">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {DOW.map((d) => (
                  <tr key={d}>
                    <td className="pr-2 text-right text-[11px] font-medium text-ink-2">{DOW_LABEL[d]}</td>
                    {hours.map((h) => {
                      const c = lookup.get(`${d}-${h}`)
                      const intensity = c ? c.orders / maxOrders : 0
                      return (
                        <td
                          key={h}
                          title={c ? `${DOW_LABEL[d]} ${h}:00 — ${c.orders} orders` : `${DOW_LABEL[d]} ${h}:00 — 0`}
                          className="h-6 w-6 rounded-[3px]"
                          style={{ background: `color-mix(in srgb, var(--chart-1) ${Math.round(intensity * 100)}%, var(--surface-2))` }}
                        />
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>Orders by day-part</CardTitle></CardHeader>
        <CardContent>
          <BarList
            rows={data.by_day_part.map((d) => ({
              label: d.day_part.replace(/_/g, ' '),
              value: d.orders,
              display: `${formatNumber(d.orders)} · ${formatCurrency(d.net_revenue)}`,
            }))}
          />
        </CardContent>
      </Card>
    </div>
  )
}
