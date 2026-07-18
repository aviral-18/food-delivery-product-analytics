import type { ColumnDef } from '@tanstack/react-table'
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAnalytics, useLabels } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { InsightsPanel } from '@/components/InsightsPanel'
import { ChartTooltip } from '@/components/charts/ChartTooltip'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatCurrency, formatNumber, formatPct } from '@/lib/utils'

interface Decile { decile: number; customers: number; avg_clv: number; total_revenue: number; revenue_share_pct: number; avg_orders: number }
interface ChannelRow { acquisition_channel: string; customers: number; avg_clv: number; avg_predicted_clv: number; avg_orders: number }
interface CityRow { city_id: number; customers: number; avg_clv: number; avg_predicted_clv: number; avg_orders: number }
interface ClvResponse {
  summary: Record<string, number>
  deciles: Decile[]
  by_channel: ChannelRow[]
  by_city: CityRow[]
}

export function ClvPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<ClvResponse>('clv', '/customers/clv')
  const { cityName } = useLabels()

  if (isLoading) return <LoadingState label="Computing lifetime value…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data || !data.deciles.length) return <EmptyState hint="No customers for the current filters." />

  const s = data.summary
  const channelCols: ColumnDef<ChannelRow, unknown>[] = [
    { accessorKey: 'acquisition_channel', header: 'Channel', cell: (c) => <span className="font-medium capitalize text-ink">{String(c.getValue()).replace(/_/g, ' ')}</span> },
    { accessorKey: 'customers', header: 'Customers', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
    { accessorKey: 'avg_clv', header: 'Avg CLV', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'avg_orders', header: 'Avg Orders', meta: { align: 'right' }, cell: (c) => (c.getValue() as number).toFixed(2) },
  ]
  const cityCols: ColumnDef<CityRow, unknown>[] = [
    { accessorKey: 'city_id', header: 'City', cell: (c) => <span className="font-medium text-ink">{cityName(c.getValue() as number)}</span> },
    { accessorKey: 'customers', header: 'Customers', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
    { accessorKey: 'avg_clv', header: 'Avg CLV', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'avg_orders', header: 'Avg Orders', meta: { align: 'right' }, cell: (c) => (c.getValue() as number).toFixed(2) },
  ]

  return (
    <div className="space-y-5">
      <StatTiles
        stats={[
          { label: 'Customers', value: formatNumber(s.customers) },
          { label: 'Avg Historical CLV', value: formatCurrency(s.avg_historical_clv_net_revenue) },
          { label: 'Avg Predicted 12m CLV', value: formatCurrency(s.avg_predicted_12m_clv_margin) },
          { label: 'Top 10% revenue share', value: formatPct(s.top_10pct_revenue_share), tone: 'warning' },
        ]}
      />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Value concentration by decile</CardTitle>
            <span className="text-[12px] text-ink-2">Customers ranked by lifetime net revenue, split into deciles (1 = most valuable).</span>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.deciles} margin={{ left: 4, right: 8, top: 8 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="decile" tickFormatter={(v) => `D${v}`} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
                <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} width={54} />
                <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={<ChartTooltip format={(v) => formatCurrency(v)} labelText={(l) => `Decile ${l}`} />} />
                <Bar isAnimationActive={false} dataKey="avg_clv" name="Avg CLV" radius={[3, 3, 0, 0]}>
                  {data.deciles.map((_, i) => (
                    <Cell key={i} fill={i === 0 ? 'var(--chart-1)' : 'color-mix(in srgb, var(--chart-1) 55%, var(--surface-3))'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <InsightsPanel page="clv" title="Value Insights" />
      </div>
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>CLV by acquisition channel</CardTitle></CardHeader>
          <CardContent><DataTable columns={channelCols} data={data.by_channel} initialSort={[{ id: 'avg_clv', desc: true }]} maxHeight="360px" /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>CLV by city</CardTitle></CardHeader>
          <CardContent><DataTable columns={cityCols} data={data.by_city} initialSort={[{ id: 'avg_clv', desc: true }]} maxHeight="360px" /></CardContent>
        </Card>
      </div>
    </div>
  )
}
