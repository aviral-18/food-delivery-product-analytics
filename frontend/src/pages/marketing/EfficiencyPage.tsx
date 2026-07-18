import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { BarList } from '@/components/charts/BarList'
import { ChartTooltip } from '@/components/charts/ChartTooltip'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatCurrency, formatMonth, formatNumber } from '@/lib/utils'

interface Channel { channel: string; spend: number; installs: number; cost_per_install: number | null }
interface Monthly { period: string; spend: number; new_customers: number; blended_cac: number | null; roas: number | null }
interface EfficiencyResponse {
  channels: Channel[]
  monthly: Monthly[]
  summary: { total_spend: number; total_new_customers: number; blended_cac: number | null; blended_roas: number | null }
}

export function EfficiencyPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<EfficiencyResponse>('mkt-eff', '/marketing/efficiency')
  if (isLoading) return <LoadingState label="Computing marketing efficiency…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const s = data.summary
  return (
    <div className="space-y-5">
      <StatTiles
        stats={[
          { label: 'Total spend', value: formatCurrency(s.total_spend) },
          { label: 'New customers', value: formatNumber(s.total_new_customers) },
          { label: 'Blended CAC', value: s.blended_cac != null ? formatCurrency(s.blended_cac) : '—' },
          { label: 'Blended ROAS', value: s.blended_roas != null ? `${s.blended_roas.toFixed(2)}×` : '—', tone: (s.blended_roas ?? 0) >= 1 ? 'good' : 'warning' },
        ]}
      />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Spend by channel</CardTitle></CardHeader>
          <CardContent>
            <BarList
              color="var(--chart-7)"
              rows={data.channels.map((c) => ({
                label: c.channel,
                value: c.spend,
                display: `${formatCurrency(c.spend)}${c.cost_per_install ? ` · ₹${c.cost_per_install}/inst` : ''}`,
              }))}
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Blended CAC & ROAS over time</CardTitle></CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data.monthly} margin={{ left: 4, right: 8, top: 8 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="period" tickFormatter={formatMonth} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} minTickGap={24} />
                <YAxis tickFormatter={(v) => formatCurrency(v)} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} width={54} />
                <Tooltip content={<ChartTooltip format={(v, k) => (k === 'roas' ? `${v.toFixed(2)}×` : formatCurrency(v))} labelText={(l) => formatMonth(String(l))} />} />
                <Line isAnimationActive={false} type="monotone" dataKey="blended_cac" name="Blended CAC" stroke="var(--chart-1)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
            <p className="mt-2 text-center text-[12px] text-muted">Marketing spend is blended across channels; CAC = spend ÷ new customers.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
