import { useState } from 'react'
import {
  Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartTooltip } from '@/components/charts/ChartTooltip'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatCurrency, formatMonth, formatNumber, cn } from '@/lib/utils'

interface ForecastResponse {
  metric: string
  history: { period: string; value: number; fitted: number }[]
  forecast: { period: string; forecast: number; lower: number; upper: number }[]
  model: { type: string; monthly_slope: number; residual_std: number; confidence: string }
  note?: string
}

const METRICS = [
  { key: 'net_revenue', label: 'Net Revenue', currency: true },
  { key: 'gmv', label: 'GMV', currency: true },
  { key: 'orders', label: 'Orders', currency: false },
]

export function ForecastPage() {
  const [metric, setMetric] = useState('net_revenue')
  const [horizon] = useState(3)
  const { data, isLoading, isError, refetch } = useAnalytics<ForecastResponse>('forecast', '/forecast', { metric, horizon })
  const currency = METRICS.find((m) => m.key === metric)?.currency ?? true
  const fmt = (v: number) => (currency ? formatCurrency(v) : formatNumber(v))

  const merged = data
    ? [
        ...data.history.map((h, i) => ({
          period: h.period,
          value: h.value,
          forecast: i === data.history.length - 1 ? h.value : undefined,
        })),
        ...data.forecast.map((f) => ({ period: f.period, forecast: f.forecast, range: [f.lower, f.upper] })),
      ]
    : []

  return (
    <div className="space-y-5">
      <div className="flex gap-2">
        {METRICS.map((m) => (
          <button
            key={m.key}
            onClick={() => setMetric(m.key)}
            className={cn(
              'h-8 rounded-md border px-3 text-[13px] font-medium transition-colors',
              metric === m.key ? 'border-primary bg-primary-soft text-primary' : 'border-border text-ink-2 hover:bg-surface-2',
            )}
          >
            {m.label}
          </button>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Forecast — next {horizon} months</CardTitle>
          {data && <span className="text-[12px] text-ink-2">{data.model.type} · {data.model.confidence}</span>}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <LoadingState label="Forecasting…" />
          ) : isError ? (
            <ErrorState onRetry={refetch} />
          ) : !data || data.history.length === 0 ? (
            <EmptyState hint={data?.note} />
          ) : (
            <ResponsiveContainer width="100%" height={360}>
              <ComposedChart data={merged} margin={{ left: 4, right: 8, top: 8 }}>
                <defs>
                  <linearGradient id="band" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--chart-1)" stopOpacity={0.18} />
                    <stop offset="100%" stopColor="var(--chart-1)" stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="period" tickFormatter={formatMonth} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} minTickGap={24} />
                <YAxis tickFormatter={fmt} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} width={56} />
                <Tooltip content={<ChartTooltip format={(v) => fmt(v)} labelText={(l) => formatMonth(String(l))} />} />
                <Area isAnimationActive={false} dataKey="range" name="95% band" stroke="none" fill="url(#band)" />
                <Line isAnimationActive={false} type="monotone" dataKey="value" name="Actual" stroke="var(--chart-1)" strokeWidth={2.5} dot={false} connectNulls />
                <Line isAnimationActive={false} type="monotone" dataKey="forecast" name="Forecast" stroke="var(--chart-4)" strokeWidth={2.5} strokeDasharray="5 4" dot={{ r: 3 }} connectNulls />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
