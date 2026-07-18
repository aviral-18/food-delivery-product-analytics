import type { ColumnDef } from '@tanstack/react-table'
import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/ui/data-table'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { InsightsPanel } from '@/components/InsightsPanel'
import { LoadingState, EmptyState, ErrorState } from '@/components/ui/misc'
import { formatCurrency, formatNumber } from '@/lib/utils'

interface Campaign {
  campaign_name: string
  redemptions: number
  discount_given: number
  net_revenue: number
  contribution_margin: number
  new_customer_orders: number
  margin_per_discount_rupee: number | null
}
interface CouponResponse {
  baseline_non_coupon: { orders: number; aov: number; avg_margin_per_order: number }
  campaigns: Campaign[]
}

export function CouponsPage() {
  const { data, isLoading, isError, refetch } = useAnalytics<CouponResponse>('coupons', '/marketing/coupons')
  if (isLoading) return <LoadingState label="Analysing coupon economics…" />
  if (isError) return <ErrorState onRetry={refetch} />
  if (!data) return <EmptyState />

  const b = data.baseline_non_coupon
  const cols: ColumnDef<Campaign, unknown>[] = [
    { accessorKey: 'campaign_name', header: 'Campaign', cell: (c) => <span className="font-medium text-ink">{c.getValue() as string}</span> },
    { accessorKey: 'redemptions', header: 'Redemptions', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
    { accessorKey: 'discount_given', header: 'Discount', meta: { align: 'right' }, cell: (c) => formatCurrency(c.getValue() as number) },
    { accessorKey: 'contribution_margin', header: 'Margin', meta: { align: 'right' }, cell: (c) => {
      const v = c.getValue() as number
      return <span className={v < 0 ? 'text-[var(--critical)]' : 'text-ink'}>{formatCurrency(v)}</span>
    } },
    { accessorKey: 'margin_per_discount_rupee', header: '₹Margin / ₹Discount', meta: { align: 'right' }, cell: (c) => {
      const v = c.getValue() as number | null
      if (v == null) return '—'
      return <span className={v <= 0 ? 'text-[var(--critical)]' : v < 0.3 ? 'text-[var(--warning)]' : 'text-[var(--good)]'}>{v.toFixed(2)}</span>
    } },
    { accessorKey: 'new_customer_orders', header: 'New Cust', meta: { align: 'right' }, cell: (c) => formatNumber(c.getValue() as number) },
  ]

  return (
    <div className="space-y-5">
      <StatTiles
        cols={3}
        stats={[
          { label: 'Non-coupon AOV', value: formatCurrency(b.aov) },
          { label: 'Non-coupon margin / order', value: formatCurrency(b.avg_margin_per_order), tone: 'good' },
          { label: 'Non-coupon orders', value: formatNumber(b.orders) },
        ]}
      />
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Campaign effectiveness</CardTitle>
            <span className="text-[12px] text-ink-2">Sorted by margin returned per ₹ of discount — the profitability lens, not just orders.</span>
          </CardHeader>
          <CardContent><DataTable columns={cols} data={data.campaigns} initialSort={[{ id: 'contribution_margin', desc: true }]} maxHeight="520px" /></CardContent>
        </Card>
        <InsightsPanel page="coupons" title="Coupon Insights" />
      </div>
    </div>
  )
}
