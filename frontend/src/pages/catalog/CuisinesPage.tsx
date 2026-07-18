import type { ColumnDef } from '@tanstack/react-table'
import { useAnalytics, useLabels } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { BarList } from '@/components/charts/BarList'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatCurrency, formatNumber } from '@/lib/utils'

interface Cuisine {
  cuisine_id: number
  orders: number
  gmv: number
  net_revenue: number
  contribution_margin: number
  aov: number
  avg_rating: number
  unique_customers: number
  restaurants: number
}

export function CuisinesPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<{ cuisines: Cuisine[] }>('cuisines', '/catalog/cuisines')
  const { cuisineName } = useLabels()
  if (isLoading) return <LoadingState label="Analysing cuisines…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data || !data.cuisines.length) return <EmptyState />

  const cols: ColumnDef<Cuisine, unknown>[] = [
    { accessorKey: 'cuisine_id', header: 'Cuisine', cell: (c) => <span className="font-medium text-ink">{cuisineName(c.getValue() as number)}</span> },
    { accessorKey: 'orders', header: 'Orders', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
    { accessorKey: 'net_revenue', header: 'Net Rev', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'contribution_margin', header: 'Margin', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'aov', header: 'AOV', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'avg_rating', header: 'Rating', meta: { align: 'right' }, cell: (c) => (c.getValue() as number).toFixed(2) },
  ]

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
      <Card className="xl:col-span-1">
        <CardHeader><CardTitle>Net revenue by cuisine</CardTitle></CardHeader>
        <CardContent>
          <BarList
            rows={[...data.cuisines].sort((a, b) => b.net_revenue - a.net_revenue).slice(0, 10).map((c) => ({
              label: cuisineName(c.cuisine_id),
              value: c.net_revenue,
              display: formatCurrency(c.net_revenue),
            }))}
          />
        </CardContent>
      </Card>
      <Card className="xl:col-span-2">
        <CardHeader><CardTitle>Cuisine performance</CardTitle></CardHeader>
        <CardContent><DataTable columns={cols} data={data.cuisines} initialSort={[{ id: 'net_revenue', desc: true }]} maxHeight="520px" /></CardContent>
      </Card>
    </div>
  )
}
