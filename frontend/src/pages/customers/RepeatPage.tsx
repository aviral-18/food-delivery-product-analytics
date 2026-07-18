import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { ChartTooltip } from '@/components/charts/ChartTooltip'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatNumber, formatPercent, formatPct } from '@/lib/utils'

interface RepeatResponse {
  summary: Record<string, number>
  order_number_retention: { order_number: number; customers: number; pct_of_activated: number; step_conversion_pct: number }[]
  days_between_buckets: { bucket: string; orders: number; share_pct: number }[]
}

const AXIS = { fontSize: 11, fill: 'var(--muted)' }

export function RepeatPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<RepeatResponse>('repeat', '/customers/repeat')
  if (isLoading) return <LoadingState label="Analysing repeat behaviour…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const s = data.summary
  return (
    <div className="space-y-5">
      <StatTiles
        stats={[
          { label: 'Repeat purchase rate', value: formatPercent(s.repeat_purchase_rate), tone: 'good' },
          { label: '1st → 2nd conversion', value: formatPercent(s.first_to_second_conversion) },
          { label: 'Avg orders / customer', value: (s.avg_orders_per_customer ?? 0).toFixed(2) },
          { label: 'Median days between', value: `${s.median_days_between_orders ?? '—'}d` },
        ]}
      />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Order-number retention</CardTitle>
            <span className="text-[12px] text-ink-2">How many activated customers reach each next order.</span>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.order_number_retention} margin={{ left: 4, right: 8, top: 8 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="order_number" tickFormatter={(v) => `#${v}`} tick={AXIS} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
                <YAxis tickFormatter={(v) => formatNumber(v)} tick={AXIS} tickLine={false} axisLine={false} width={44} />
                <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={<ChartTooltip format={(v) => formatNumber(v)} labelText={(l) => `Order #${l}`} />} />
                <Bar isAnimationActive={false} dataKey="customers" name="Customers" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Days between orders</CardTitle>
            <span className="text-[12px] text-ink-2">Distribution of gaps between consecutive orders.</span>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.days_between_buckets} margin={{ left: 4, right: 8, top: 8 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="bucket" tick={AXIS} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
                <YAxis tickFormatter={(v) => `${v}%`} tick={AXIS} tickLine={false} axisLine={false} width={40} />
                <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={<ChartTooltip format={(v) => formatPct(v)} />} />
                <Bar isAnimationActive={false} dataKey="share_pct" name="Share" fill="var(--chart-5)" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
