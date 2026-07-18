import type { ColumnDef } from '@tanstack/react-table'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAnalytics, useLabels } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { ChartTooltip } from '@/components/charts/ChartTooltip'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatNumber, formatPercent } from '@/lib/utils'

interface CityRow { city_id: number; delivered_orders: number; avg_delivery_minutes: number; late_rate: number }
interface DeliveryResponse {
  overall: Record<string, number>
  by_city: CityRow[]
  delivery_time_distribution: { bucket: string; orders: number }[]
}

export function DeliveryPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<DeliveryResponse>('delivery', '/operations/delivery')
  const { cityName } = useLabels()
  if (isLoading) return <LoadingState label="Analysing delivery performance…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const o = data.overall
  const cols: ColumnDef<CityRow, unknown>[] = [
    { accessorKey: 'city_id', header: 'City', cell: (c) => <span className="font-medium text-ink">{cityName(c.getValue() as number)}</span> },
    { accessorKey: 'delivered_orders', header: 'Delivered', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
    { accessorKey: 'avg_delivery_minutes', header: 'Avg Time', meta: { align: 'right' }, cell: (c) => `${(c.getValue() as number).toFixed(1)}m` },
    { accessorKey: 'late_rate', header: 'Late Rate', meta: { align: 'right' }, cell: (c) => <span className={(c.getValue() as number) > 0.25 ? 'text-[var(--critical)]' : 'text-ink'}>{formatPercent(c.getValue() as number)}</span> },
  ]

  return (
    <div className="space-y-5">
      <StatTiles
        stats={[
          { label: 'Avg delivery time', value: `${o.avg_delivery_minutes} min` },
          { label: 'Late rate', value: formatPercent(o.late_rate), tone: o.late_rate > 0.25 ? 'critical' : 'default' },
          { label: 'Avg prep time', value: `${o.avg_prep_minutes} min` },
          { label: 'Avg delivery rating', value: (o.avg_delivery_rating ?? 0).toFixed(2), tone: 'good' },
        ]}
      />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Delivery-time distribution</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.delivery_time_distribution} margin={{ left: 4, right: 8, top: 8 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
                <YAxis tickFormatter={(v) => formatNumber(v)} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} width={44} />
                <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={<ChartTooltip format={(v) => formatNumber(v)} labelText={(l) => `${l} min`} />} />
                <Bar isAnimationActive={false} dataKey="orders" name="Orders" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Performance by city</CardTitle></CardHeader>
          <CardContent><DataTable columns={cols} data={data.by_city} initialSort={[{ id: 'late_rate', desc: true }]} maxHeight="320px" /></CardContent>
        </Card>
      </div>
    </div>
  )
}
