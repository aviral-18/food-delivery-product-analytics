import { useEffect, useMemo, useState } from 'react'
import { FlaskConical, Info, RotateCcw } from 'lucide-react'
import { api } from '@/lib/api'
import { useFilters } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/misc'
import { formatCurrency, formatNumber, formatPercent, cn } from '@/lib/utils'

interface LeverConfig {
  key: string
  label: string
  unit: string
  min: number
  max: number
  step: number
  help: string
}

const LEVERS: LeverConfig[] = [
  { key: 'reduce_coupon_value', label: 'Reduce coupon value', unit: '%', min: 0, max: 100, step: 5, help: 'Cut average coupon discount by this %.' },
  { key: 'increase_delivery_fee', label: 'Increase delivery fee', unit: '₹', min: 0, max: 50, step: 5, help: 'Add this many ₹ to the delivery fee per order.' },
  { key: 'improve_delivery_time', label: 'Improve delivery time', unit: 'min', min: 0, max: 20, step: 1, help: 'Make average delivery this many minutes faster.' },
  { key: 'add_restaurants', label: 'Add restaurant supply', unit: '%', min: 0, max: 100, step: 5, help: 'Increase active restaurant supply by this %.' },
  { key: 'increase_marketing_spend', label: 'Increase marketing spend', unit: '%', min: 0, max: 100, step: 5, help: 'Increase acquisition budget by this %.' },
  { key: 'change_free_delivery_threshold', label: 'Free-delivery threshold', unit: '₹', min: -200, max: 200, step: 25, help: 'Change the free-delivery order threshold (₹).' },
]

interface ResultMetric {
  baseline: number
  simulated: number
  delta: number
  delta_pct: number | null
}
interface SimResult {
  disclaimer: string
  levers_applied: { lever: string; magnitude: number; assumptions: string[]; order_change_pct: number }[]
  results: Record<string, ResultMetric>
}

const RESULT_META: { key: string; label: string; fmt: (n: number) => string; invert?: boolean }[] = [
  { key: 'delivered_orders', label: 'Delivered Orders', fmt: (n) => formatNumber(n) },
  { key: 'gmv', label: 'GMV', fmt: (n) => formatCurrency(n) },
  { key: 'net_revenue', label: 'Net Revenue', fmt: (n) => formatCurrency(n) },
  { key: 'contribution_margin', label: 'Contribution Margin', fmt: (n) => formatCurrency(n) },
  { key: 'repeat_purchase_rate', label: 'Repeat Rate', fmt: (n) => formatPercent(n) },
]

export function DecisionLabPage() {
  const { filters } = useFilters()
  const [values, setValues] = useState<Record<string, number>>({})
  const [result, setResult] = useState<SimResult | null>(null)
  const [loading, setLoading] = useState(false)

  const activeLevers = useMemo(
    () => Object.entries(values).filter(([, v]) => v !== 0).map(([lever, magnitude]) => ({ lever, magnitude })),
    [values],
  )

  useEffect(() => {
    const t = setTimeout(async () => {
      setLoading(true)
      try {
        const res = await api.post<SimResult>('/decision-lab/simulate', { levers: activeLevers }, { params: filters })
        setResult(res.data)
      } finally {
        setLoading(false)
      }
    }, 350)
    return () => clearTimeout(t)
  }, [activeLevers, filters])

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      {/* Levers */}
      <Card className="lg:col-span-1">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-primary" />
            Scenario levers
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-5">
          {LEVERS.map((l) => {
            const v = values[l.key] ?? 0
            return (
              <div key={l.key}>
                <div className="mb-1 flex items-center justify-between">
                  <label className="text-[13px] font-medium text-ink">{l.label}</label>
                  <span className={cn('tabnum text-[13px] font-semibold', v !== 0 ? 'text-primary' : 'text-muted')}>
                    {v > 0 && l.min >= 0 ? '+' : ''}
                    {v}
                    {l.unit}
                  </span>
                </div>
                <input
                  type="range"
                  min={l.min}
                  max={l.max}
                  step={l.step}
                  value={v}
                  onChange={(e) => setValues((s) => ({ ...s, [l.key]: Number(e.target.value) }))}
                  className="w-full accent-[var(--primary)]"
                />
                <p className="mt-0.5 text-[11px] text-muted">{l.help}</p>
              </div>
            )
          })}
          <Button variant="secondary" size="sm" onClick={() => setValues({})} className="w-full">
            <RotateCcw className="h-3.5 w-3.5" /> Reset scenario
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      <div className="space-y-5 lg:col-span-2">
        <div className="flex items-start gap-2 rounded-[var(--radius-md)] border border-border bg-primary-soft/40 p-3 text-[12px] text-ink-2">
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <span>{result?.disclaimer ?? 'Adjust levers to estimate impact. Outputs are simulation estimates from historical elasticities.'}</span>
        </div>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          {RESULT_META.map((m) => {
            const r = result?.results[m.key]
            const dp = r?.delta_pct ?? 0
            const positive = dp >= 0
            return (
              <div key={m.key} className="rounded-[var(--radius-card)] border border-border bg-surface p-4">
                <div className="text-[12px] font-medium text-ink-2">{m.label}</div>
                <div className="mt-1.5 flex items-center gap-2">
                  {loading && !result ? (
                    <Spinner className="h-4 w-4" />
                  ) : (
                    <span className="text-[19px] font-semibold tabnum text-ink">
                      {r ? m.fmt(r.simulated) : '—'}
                    </span>
                  )}
                </div>
                {r && activeLevers.length > 0 && (
                  <div className={cn('mt-1 text-[12px] font-medium', positive ? 'text-[var(--good)]' : 'text-[var(--critical)]')}>
                    {positive ? '+' : ''}
                    {dp.toFixed(1)}% vs baseline
                  </div>
                )}
                {r && activeLevers.length === 0 && <div className="mt-1 text-[12px] text-muted">baseline</div>}
              </div>
            )
          })}
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Applied levers & assumptions</CardTitle>
          </CardHeader>
          <CardContent>
            {result && result.levers_applied.length > 0 ? (
              <div className="space-y-3">
                {result.levers_applied.map((l) => (
                  <div key={l.lever} className="rounded-[var(--radius-md)] border border-border bg-surface-2 p-3">
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-[13px] font-medium text-ink">
                        {LEVERS.find((x) => x.key === l.lever)?.label ?? l.lever}
                      </span>
                      <span className="tabnum text-[12px] text-ink-2">order impact {l.order_change_pct >= 0 ? '+' : ''}{l.order_change_pct}%</span>
                    </div>
                    <ul className="list-inside list-disc text-[12px] text-muted">
                      {l.assumptions.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-6 text-center text-[13px] text-muted">
                Move a lever to simulate a product or pricing decision.
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
