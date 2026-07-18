import { ArrowDownRight, ArrowUpRight } from 'lucide-react'
import type { KpiCard as Kpi } from '@/types'
import { formatByType } from '@/lib/utils'
import { cn } from '@/lib/utils'

const LABELS: Record<string, string> = {
  net_revenue: 'Net Revenue',
  gmv: 'GMV',
  delivered_orders: 'Delivered Orders',
  aov: 'Avg Order Value',
  active_customers: 'Active Customers',
  new_customers: 'New Customers',
  repeat_purchase_rate: 'Repeat Rate',
  contribution_margin: 'Contribution Margin',
  contribution_margin_pct: 'CM % of GMV',
  avg_delivery_minutes: 'Avg Delivery Time',
  late_delivery_rate: 'Late Delivery',
  cancellation_rate: 'Cancellation Rate',
  refund_rate: 'Refund Rate',
  coupon_redemption_rate: 'Coupon Redemption',
}

export function KpiCard({ kpi }: { kpi: Kpi }) {
  const label = LABELS[kpi.key] ?? kpi.key
  const hasDelta = kpi.delta_pct !== null && kpi.delta_pct !== undefined
  const positive = kpi.is_positive
  const up = (kpi.delta_pct ?? 0) >= 0

  return (
    <div className="rounded-[var(--radius-card)] border border-border bg-surface p-4 transition-colors hover:border-border-strong">
      <div className="text-[12px] font-medium text-ink-2">{label}</div>
      <div className="mt-1.5 text-[22px] font-semibold tracking-tight text-ink tabnum">
        {formatByType(kpi.value, kpi.format)}
      </div>
      {hasDelta ? (
        <div className="mt-1.5 flex items-center gap-1 text-[12px]">
          <span
            className={cn(
              'inline-flex items-center gap-0.5 font-medium',
              positive ? 'text-[var(--good)]' : 'text-[var(--critical)]',
            )}
          >
            {up ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
            {Math.abs(kpi.delta_pct as number).toFixed(1)}%
          </span>
          <span className="text-muted">vs prev period</span>
        </div>
      ) : (
        <div className="mt-1.5 text-[12px] text-muted">no prior period</div>
      )}
    </div>
  )
}
