import type { ColumnDef } from '@tanstack/react-table'
import { useAnalytics, useLabels } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { InsightsPanel } from '@/components/InsightsPanel'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatCurrency, formatNumber, formatPercent } from '@/lib/utils'

interface City {
  city_id: number
  orders: number
  net_revenue: number
  contribution_margin: number
  aov: number
  active_customers: number
  new_customers: number
  active_restaurants: number
  late_rate: number
  marketing_spend: number
  cac: number | null
  roas: number | null
}

export function CitiesPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<{ cities: City[] }>('cities', '/catalog/cities')
  const { cityName } = useLabels()
  if (isLoading) return <LoadingState label="Analysing cities…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data || !data.cities.length) return <EmptyState />

  const cols: ColumnDef<City, unknown>[] = [
    { accessorKey: 'city_id', header: 'City', cell: (c) => <span className="font-medium text-ink">{cityName(c.getValue() as number)}</span> },
    { accessorKey: 'net_revenue', header: 'Net Rev', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'contribution_margin', header: 'Margin', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'active_customers', header: 'Active Cust', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
    { accessorKey: 'marketing_spend', header: 'Spend', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'cac', header: 'CAC', meta: { align: 'right' }, cell: (c) => (c.getValue() != null ? formatCurrency(c.getValue() as number) : '—') },
    { accessorKey: 'roas', header: 'ROAS', meta: { align: 'right' }, cell: (c) => {
      const v = c.getValue() as number | null
      if (v == null) return '—'
      return <span className={v >= 1.5 ? 'text-[var(--good)]' : v < 1 ? 'text-[var(--critical)]' : 'text-ink'}>{v.toFixed(2)}×</span>
    } },
    { accessorKey: 'late_rate', header: 'Late', meta: { align: 'right' }, cell: (c) => formatPercent(c.getValue() as number) },
  ]

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
      <Card className="xl:col-span-2">
        <CardHeader><CardTitle>City performance & marketing efficiency</CardTitle></CardHeader>
        <CardContent><DataTable columns={cols} data={data.cities} initialSort={[{ id: 'net_revenue', desc: true }]} maxHeight="560px" /></CardContent>
      </Card>
      <InsightsPanel page="city" title="City Insights" />
    </div>
  )
}
