import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { InsightsPanel } from '@/components/InsightsPanel'
import { ChartTooltip } from '@/components/charts/ChartTooltip'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatMonth } from '@/lib/utils'

interface Cohort {
  cohort: string
  size: number
  values: { period: number; customers: number; retention_pct: number }[]
}
interface CohortResponse {
  cohorts: Cohort[]
  retention_curve: { period: number; retention_pct: number }[]
}

function cellStyle(pct: number) {
  // Sequential blue: blend chart-1 into the surface by retention strength.
  return {
    background: `color-mix(in srgb, var(--chart-1) ${Math.max(4, pct)}%, var(--surface))`,
    color: pct > 42 ? '#fff' : 'var(--ink-2)',
  }
}

export function CohortsPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<CohortResponse>('cohorts', '/customers/cohorts')

  if (isLoading) return <LoadingState label="Computing cohort retention…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data || data.cohorts.length === 0) return <EmptyState hint="No cohorts for the current filters." />

  const maxPeriod = Math.max(...data.cohorts.flatMap((c) => c.values.map((v) => v.period)))
  const periods = Array.from({ length: maxPeriod + 1 }, (_, i) => i)

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
      <div className="space-y-5 xl:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>Retention Matrix — acquisition cohorts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="border-separate border-spacing-[3px] text-[12px]">
                <thead>
                  <tr>
                    <th className="sticky left-0 z-10 bg-surface px-2 py-1 text-left text-[11px] font-medium text-muted">
                      Cohort
                    </th>
                    <th className="px-2 py-1 text-right text-[11px] font-medium text-muted">Size</th>
                    {periods.map((p) => (
                      <th key={p} className="px-1 py-1 text-center text-[11px] font-medium text-muted">
                        M{p}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.cohorts.map((c) => (
                    <tr key={c.cohort}>
                      <td className="sticky left-0 z-10 whitespace-nowrap bg-surface px-2 py-1 font-medium text-ink">
                        {formatMonth(c.cohort)}
                      </td>
                      <td className="px-2 py-1 text-right tabnum text-ink-2">{c.size.toLocaleString('en-IN')}</td>
                      {periods.map((p) => {
                        const cell = c.values.find((v) => v.period === p)
                        if (!cell) return <td key={p} />
                        return (
                          <td
                            key={p}
                            title={`${cell.customers} customers`}
                            className="rounded px-1.5 py-1 text-center tabnum"
                            style={cellStyle(cell.retention_pct)}
                          >
                            {cell.retention_pct.toFixed(0)}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-[12px] text-muted">
              Each cell is the % of a signup cohort still ordering N months later. Read down a column to
              compare cohort quality over time — declining columns mean newer cohorts retain worse.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Average retention curve</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={data.retention_curve} margin={{ left: 4, right: 8, top: 8 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="period" tickFormatter={(v) => `M${v}`} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={{ stroke: 'var(--grid)' }} />
                <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11, fill: 'var(--muted)' }} tickLine={false} axisLine={false} width={38} />
                <Tooltip content={<ChartTooltip format={(v) => `${v.toFixed(1)}%`} labelText={(l) => `Month ${l}`} />} />
                <Line isAnimationActive={false} type="monotone" dataKey="retention_pct" name="Retention" stroke="var(--chart-1)" strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <InsightsPanel page="retention" />
    </div>
  )
}
