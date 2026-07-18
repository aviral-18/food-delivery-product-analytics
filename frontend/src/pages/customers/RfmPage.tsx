import { useMemo } from 'react'
import type { ColumnDef } from '@tanstack/react-table'
import {
  Cell, Scatter, ScatterChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { InsightsPanel } from '@/components/InsightsPanel'
import { LoadingState, EmptyState, ErrorState, Badge } from '@/components/ui/misc'
import { formatCurrency, formatNumber, formatPct } from '@/lib/utils'

interface Segment {
  segment: string
  customers: number
  share_pct: number
  avg_recency_days: number
  avg_frequency: number
  avg_monetary: number
  total_net_revenue: number
  revenue_share_pct: number
}
interface ScatterPoint {
  customer_id: number
  recency_days: number
  frequency: number
  monetary: number
  segment: string
}
interface RfmResponse {
  customers_scored: number
  segments: Segment[]
  scatter_sample: ScatterPoint[]
}

const columns: ColumnDef<Segment, unknown>[] = [
  { accessorKey: 'segment', header: 'Segment', cell: (c) => <span className="font-medium text-ink">{c.getValue() as string}</span> },
  { accessorKey: 'customers', header: 'Customers', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
  { accessorKey: 'share_pct', header: 'Share', meta: { align: 'right' }, cell: (c) => formatPct(c.getValue() as number) },
  { accessorKey: 'revenue_share_pct', header: 'Revenue Share', meta: { align: 'right' }, cell: (c) => formatPct(c.getValue() as number) },
  { accessorKey: 'avg_frequency', header: 'Avg Freq', meta: { align: 'right' }, cell: (c) => (c.getValue() as number).toFixed(1) },
  { accessorKey: 'avg_recency_days', header: 'Avg Recency', meta: { align: 'right' }, cell: (c) => `${(c.getValue() as number).toFixed(0)}d` },
  { accessorKey: 'avg_monetary', header: 'Avg Spend', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
]

export function RfmPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<RfmResponse>('rfm', '/customers/rfm')

  const { points, maxMon } = useMemo(() => {
    const pts = data?.scatter_sample ?? []
    return { points: pts, maxMon: Math.max(1, ...pts.map((p) => p.monetary)) }
  }, [data])

  if (isLoading) return <LoadingState label="Scoring customers (RFM)…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data || data.segments.length === 0) return <EmptyState hint="No customers to score for these filters." />

  const top = data.segments[0]
  return (
    <div className="space-y-5">
      <StatTiles
        stats={[
          { label: 'Customers scored', value: formatNumber(data.customers_scored) },
          { label: 'Segments', value: data.segments.length },
          { label: 'Top segment', value: top.segment, hint: `${formatPct(top.revenue_share_pct)} of revenue` },
          { label: 'At-risk + hibernating', value: formatPct(
              data.segments.filter((s) => ['At Risk', 'Hibernating', "Can't Lose Them", 'Lost'].includes(s.segment))
                .reduce((a, s) => a + s.share_pct, 0),
            ), tone: 'warning' },
        ]}
      />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Recency vs Frequency</CardTitle>
            <span className="text-[12px] text-ink-2">Each dot is a customer; darker = higher spend (monetary).</span>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={340}>
              <ScatterChart margin={{ left: 4, right: 12, top: 8, bottom: 8 }}>
                <CartesianGrid stroke="var(--grid)" />
                <XAxis type="number" dataKey="recency_days" name="Recency (days)" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} label={{ value: 'Recency (days) →', position: 'insideBottom', offset: -4, fontSize: 11, fill: 'var(--muted)' }} />
                <YAxis type="number" dataKey="frequency" name="Frequency" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} width={34} />
                <ZAxis type="number" dataKey="monetary" range={[24, 240]} />
                <Tooltip
                  cursor={{ strokeDasharray: '3 3', stroke: 'var(--muted)' }}
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null
                    const p = payload[0].payload as ScatterPoint
                    return (
                      <div className="rounded-lg border border-border bg-[var(--glass)] px-3 py-2 text-[12px] shadow-[var(--shadow)] backdrop-blur-md">
                        <div className="font-medium text-ink">Customer #{p.customer_id}</div>
                        <div className="text-ink-2">{p.segment}</div>
                        <div className="mt-1 text-muted">
                          {p.frequency} orders · {p.recency_days}d ago · {formatCurrency(p.monetary)}
                        </div>
                      </div>
                    )
                  }}
                />
                <Scatter data={points} fillOpacity={0.8}>
                  {points.map((p, i) => {
                    const t = Math.min(1, p.monetary / maxMon)
                    return <Cell key={i} fill={`color-mix(in srgb, var(--chart-1) ${25 + 70 * t}%, var(--surface-3))`} />
                  })}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <InsightsPanel page="retention" title="Segment Insights" />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Segment breakdown
            <Badge tone="primary">{data.segments.length} segments</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable columns={columns} data={data.segments} initialSort={[{ id: 'revenue_share_pct', desc: true }]} />
        </CardContent>
      </Card>
    </div>
  )
}
