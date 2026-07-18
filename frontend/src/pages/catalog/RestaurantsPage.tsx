import type { ColumnDef } from '@tanstack/react-table'
import { useAnalytics, useLabels } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { LoadingState, EmptyState, ErrorState, Badge } from '@/components/ui/misc'
import { formatCurrency, formatNumber, formatPercent } from '@/lib/utils'

interface Row {
  restaurant_id: number
  restaurant_name: string
  city_id: number
  net_revenue: number
  delivered_orders: number
  avg_rating: number
  late_rate: number
  performance_score?: number
}
interface RankingResponse { top: Row[]; bottom: Row[]; total_ranked: number }

export function RestaurantsPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<RankingResponse>('rest-rank', '/catalog/restaurants/ranking', { limit: 15 })
  const { cityName } = useLabels()
  if (isLoading) return <LoadingState label="Ranking restaurants…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const nameCol: ColumnDef<Row, unknown> = {
    accessorKey: 'restaurant_name', header: 'Restaurant',
    cell: (c) => (
      <div>
        <div className="font-medium text-ink">{c.getValue() as string}</div>
        <div className="text-[11px] text-muted">{cityName(c.row.original.city_id)}</div>
      </div>
    ),
  }
  const topCols: ColumnDef<Row, unknown>[] = [
    nameCol,
    { accessorKey: 'performance_score', header: 'Score', meta: { align: 'right' }, cell: (c) => <Badge tone="primary">{(c.getValue() as number)?.toFixed(0)}</Badge> },
    { accessorKey: 'net_revenue', header: 'Net Rev', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'avg_rating', header: 'Rating', meta: { align: 'right' }, cell: (c) => (c.getValue() as number).toFixed(2) },
    { accessorKey: 'late_rate', header: 'Late', meta: { align: 'right' }, cell: (c) => formatPercent(c.getValue() as number) },
  ]
  const botCols: ColumnDef<Row, unknown>[] = [
    nameCol,
    { accessorKey: 'avg_rating', header: 'Rating', meta: { align: 'right' }, cell: (c) => <span className="text-[var(--critical)]">{(c.getValue() as number).toFixed(2)}</span> },
    { accessorKey: 'late_rate', header: 'Late', meta: { align: 'right' }, cell: (c) => formatPercent(c.getValue() as number) },
    { accessorKey: 'delivered_orders', header: 'Orders', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
  ]

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>Top performers</CardTitle><span className="text-[12px] text-ink-2">Composite of revenue, rating & reliability.</span></CardHeader>
        <CardContent><DataTable columns={topCols} data={data.top} initialSort={[{ id: 'performance_score', desc: true }]} maxHeight="520px" /></CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2">Needs attention <Badge tone="critical">poor experience</Badge></CardTitle><span className="text-[12px] text-ink-2">Low ratings among restaurants with real volume.</span></CardHeader>
        <CardContent><DataTable columns={botCols} data={data.bottom} initialSort={[{ id: 'avg_rating', desc: false }]} maxHeight="520px" /></CardContent>
      </Card>
    </div>
  )
}
