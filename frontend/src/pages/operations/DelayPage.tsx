import { useAnalytics, useLabels } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { BarList } from '@/components/charts/BarList'
import { InsightsPanel } from '@/components/InsightsPanel'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatPct } from '@/lib/utils'

interface DimRow { dimension: string | number; delivered_orders: number; avg_delivery_minutes: number; late_rate: number }
interface DelayResponse {
  decomposition: Record<string, number>
  late_rate_by_weather: DimRow[]
  late_rate_by_day_part: DimRow[]
  late_rate_by_city: DimRow[]
  late_rate_by_distance: DimRow[]
}

function toRows(rows: DimRow[], label?: (d: string | number) => string) {
  return rows.map((r) => ({
    label: label ? label(r.dimension) : String(r.dimension).replace(/_/g, ' '),
    value: r.late_rate * 100,
    display: formatPct(r.late_rate * 100),
    tone:
      r.late_rate > 0.5 ? 'var(--critical)' : r.late_rate > 0.3 ? 'var(--serious)' : 'var(--chart-1)',
  }))
}

export function DelayPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<DelayResponse>('delay', '/operations/delay-root-cause')
  const { cityName } = useLabels()
  if (isLoading) return <LoadingState label="Decomposing delivery delays…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const d = data.decomposition
  return (
    <div className="space-y-5">
      <StatTiles
        stats={[
          { label: 'Avg total time', value: `${d.avg_total_minutes} min` },
          { label: 'Avg prep time', value: `${d.avg_prep_minutes} min`, hint: `${d.prep_share_of_total_pct}% of total` },
          { label: 'Avg travel + wait', value: `${d.avg_travel_and_wait_minutes} min` },
          { label: 'Avg distance', value: `${d.avg_distance_km} km` },
        ]}
      />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Late rate by weather</CardTitle>
              <span className="text-[12px] text-ink-2">Adverse weather is the biggest SLA shock.</span>
            </CardHeader>
            <CardContent><BarList rows={toRows(data.late_rate_by_weather)} /></CardContent>
          </Card>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>By distance</CardTitle></CardHeader>
              <CardContent><BarList rows={toRows(data.late_rate_by_distance)} /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>By city (worst first)</CardTitle></CardHeader>
              <CardContent><BarList rows={toRows(data.late_rate_by_city.slice(0, 8), cityName as (d: string | number) => string)} /></CardContent>
            </Card>
          </div>
        </div>
        <InsightsPanel page="delivery" title="Delay Insights" />
      </div>
    </div>
  )
}
