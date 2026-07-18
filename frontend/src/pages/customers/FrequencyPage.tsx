import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { ChartTooltip } from '@/components/charts/ChartTooltip'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatNumber, formatPct } from '@/lib/utils'

interface FreqResponse {
  distribution: { bucket: string; customers: number; share_pct: number }[]
  total_customers: number
}

export function FrequencyPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<FreqResponse>('frequency', '/customers/order-frequency')
  if (isLoading) return <LoadingState label="Building frequency distribution…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const oneAndDone = data.distribution.find((d) => d.bucket === '1')?.share_pct ?? 0
  const power = data.distribution.filter((d) => ['10-19', '20+'].includes(d.bucket)).reduce((a, d) => a + d.share_pct, 0)

  return (
    <div className="space-y-5">
      <StatTiles
        cols={3}
        stats={[
          { label: 'Customers', value: formatNumber(data.total_customers) },
          { label: 'One-and-done', value: formatPct(oneAndDone), tone: 'warning', hint: 'ordered exactly once' },
          { label: 'Power users (10+)', value: formatPct(power), tone: 'good' },
        ]}
      />
      <Card>
        <CardHeader>
          <CardTitle>Orders-per-customer distribution</CardTitle>
          <span className="text-[12px] text-ink-2">A long tail: a small share of customers place most orders.</span>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={data.distribution} margin={{ left: 4, right: 8, top: 8 }}>
              <CartesianGrid stroke="var(--grid)" vertical={false} />
              <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
              <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} width={40} />
              <Tooltip cursor={{ fill: 'var(--surface-2)' }} content={<ChartTooltip format={(v) => formatPct(v)} labelText={(l) => `${l} orders`} />} />
              <Bar isAnimationActive={false} dataKey="share_pct" name="Share of customers" fill="var(--chart-1)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
