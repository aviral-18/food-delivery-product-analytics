import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, Line, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from 'recharts'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/misc'
import { KpiCard } from '@/components/dashboard/KpiCard'
import { HealthIndex } from '@/components/dashboard/HealthIndex'
import { InsightsPanel } from '@/components/InsightsPanel'
import { ChartTooltip } from '@/components/charts/ChartTooltip'
import { formatCurrency, formatMonth, formatNumber } from '@/lib/utils'
import type { KpiCard as Kpi } from '@/types'

const AXIS = { fontSize: 11, fill: 'var(--muted)' }

interface TrendPoint {
  period: string
  gmv: number
  net_revenue: number
  contribution_margin: number
}
interface GrowthPoint {
  period: string
  new_customers: number
  returning_customers: number
}

export function DashboardPage() {
  const kpis = useAnalytics<{ cards: Kpi[] }>('kpis', '/executive/kpis')
  const trend = useAnalytics<{ series: TrendPoint[] }>('trend', '/executive/revenue-trend', { grain: 'month' })
  const growth = useAnalytics<{ series: GrowthPoint[] }>('growth', '/executive/growth')

  return (
    <div className="space-y-5">
      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
        {kpis.isLoading
          ? Array.from({ length: 14 }).map((_, i) => <Skeleton key={i} className="h-[92px]" />)
          : kpis.data?.cards.map((k) => <KpiCard key={k.key} kpi={k} />)}
      </div>

      {/* Revenue trend + Health */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Revenue Trend</CardTitle>
          </CardHeader>
          <CardContent>
            {trend.isLoading || !trend.data ? (
              <Skeleton className="h-[280px] w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <AreaChart data={trend.data.series} margin={{ left: 4, right: 8, top: 8 }}>
                  <defs>
                    <linearGradient id="gGmv" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="period" tickFormatter={formatMonth} tick={AXIS} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} minTickGap={20} />
                  <YAxis tickFormatter={(v) => formatCurrency(v)} tick={AXIS} tickLine={false} axisLine={false} width={54} />
                  <Tooltip
                    content={<ChartTooltip format={(v) => formatCurrency(v)} labelText={(l) => formatMonth(String(l))} />}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: 'var(--ink-2)' }} />
                  <Area isAnimationActive={false} type="monotone" dataKey="gmv" name="GMV" stroke="var(--chart-1)" strokeWidth={2} fill="url(#gGmv)" />
                  <Line isAnimationActive={false} type="monotone" dataKey="net_revenue" name="Net Revenue" stroke="var(--chart-2)" strokeWidth={2} dot={false} />
                  <Line isAnimationActive={false} type="monotone" dataKey="contribution_margin" name="Contribution Margin" stroke="var(--chart-4)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <HealthIndex />
      </div>

      {/* Growth + Insights */}
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Customer Growth — New vs Returning</CardTitle>
          </CardHeader>
          <CardContent>
            {growth.isLoading || !growth.data ? (
              <Skeleton className="h-[260px] w-full" />
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={growth.data.series} margin={{ left: 4, right: 8, top: 8 }} barCategoryGap="22%">
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="period" tickFormatter={formatMonth} tick={AXIS} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} minTickGap={20} />
                  <YAxis tickFormatter={(v) => formatNumber(v)} tick={AXIS} tickLine={false} axisLine={false} width={44} />
                  <Tooltip
                    cursor={{ fill: 'var(--surface-2)' }}
                    content={<ChartTooltip format={(v) => formatNumber(v)} labelText={(l) => formatMonth(String(l))} />}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12, color: 'var(--ink-2)' }} />
                  <Bar isAnimationActive={false} dataKey="new_customers" name="New" stackId="a" fill="var(--chart-1)" radius={[0, 0, 0, 0]} />
                  <Bar isAnimationActive={false} dataKey="returning_customers" name="Returning" stackId="a" fill="var(--chart-5)" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <InsightsPanel page="executive" />
      </div>
    </div>
  )
}
