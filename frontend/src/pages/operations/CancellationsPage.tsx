import type { ColumnDef } from '@tanstack/react-table'
import { useAnalytics, useLabels } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { BarList } from '@/components/charts/BarList'
import { InsightsPanel } from '@/components/InsightsPanel'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatNumber, formatPercent } from '@/lib/utils'

interface CityRow { city_id: number; total_orders: number; cancelled_orders: number; cancel_rate: number }
interface CancelResponse {
  total_orders: number
  cancelled_orders: number
  cancellation_rate: number
  by_reason: { reason: string; orders: number }[]
  by_city: CityRow[]
}

export function CancellationsPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<CancelResponse>('cancel', '/operations/cancellations')
  const { cityName } = useLabels()
  if (isLoading) return <LoadingState label="Analysing cancellations…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const cols: ColumnDef<CityRow, unknown>[] = [
    { accessorKey: 'city_id', header: 'City', cell: (c) => <span className="font-medium text-ink">{cityName(c.getValue() as number)}</span> },
    { accessorKey: 'total_orders', header: 'Orders', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
    { accessorKey: 'cancelled_orders', header: 'Cancelled', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
    { accessorKey: 'cancel_rate', header: 'Rate', meta: { align: 'right' }, cell: (c) => <span className={(c.getValue() as number) > 0.07 ? 'text-[var(--critical)]' : 'text-ink'}>{formatPercent(c.getValue() as number)}</span> },
  ]

  return (
    <div className="space-y-5">
      <StatTiles
        cols={3}
        stats={[
          { label: 'Cancellation rate', value: formatPercent(data.cancellation_rate), tone: data.cancellation_rate > 0.07 ? 'critical' : 'default' },
          { label: 'Cancelled orders', value: formatNumber(data.cancelled_orders) },
          { label: 'Total orders', value: formatNumber(data.total_orders) },
        ]}
      />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Card>
            <CardHeader><CardTitle>Cancellation reasons</CardTitle></CardHeader>
            <CardContent>
              <BarList
                color="var(--chart-6)"
                rows={data.by_reason.map((r) => ({ label: r.reason.replace(/_/g, ' '), value: r.orders, display: formatNumber(r.orders) }))}
              />
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle>By city</CardTitle></CardHeader>
            <CardContent><DataTable columns={cols} data={data.by_city} initialSort={[{ id: 'cancel_rate', desc: true }]} maxHeight="320px" /></CardContent>
          </Card>
        </div>
        <InsightsPanel page="cancellation" title="Cancellation Insights" />
      </div>
    </div>
  )
}
