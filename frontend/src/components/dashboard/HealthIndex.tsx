import { useAnalytics } from '@/state/FiltersProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/misc'
import { scoreColor } from '@/lib/palette'

interface HealthData {
  overall_score: number
  grade: string
  subscores: Record<string, number>
  weights: Record<string, number>
}

const LABELS: Record<string, string> = {
  growth: 'Growth',
  retention: 'Retention',
  unit_economics: 'Unit Economics',
  experience: 'Experience',
  operations: 'Operations',
}

function Gauge({ score, grade }: { score: number; grade: string }) {
  const r = 52
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, score)) / 100
  const color = scoreColor(score)
  return (
    <div className="relative h-[140px] w-[140px]">
      <svg viewBox="0 0 140 140" className="h-full w-full -rotate-90">
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--surface-3)" strokeWidth="10" />
        <circle
          cx="70"
          cy="70"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
          style={{ transition: 'stroke-dashoffset 0.8s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[30px] font-semibold leading-none tabnum text-ink">{Math.round(score)}</span>
        <span className="mt-0.5 text-[11px] text-muted">Grade {grade}</span>
      </div>
    </div>
  )
}

export function HealthIndex() {
  const { data, isLoading } = useAnalytics<HealthData>('health', '/executive/health-index')

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Product Health Index</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading || !data ? (
          <Skeleton className="h-52 w-full" />
        ) : (
          <div className="flex flex-col items-center gap-4">
            <Gauge score={data.overall_score} grade={data.grade} />
            <div className="w-full space-y-2.5">
              {Object.entries(data.subscores).map(([key, val]) => (
                <div key={key}>
                  <div className="mb-1 flex items-center justify-between text-[12px]">
                    <span className="text-ink-2">{LABELS[key] ?? key}</span>
                    <span className="tabnum font-medium text-ink">{Math.round(val)}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${val}%`, background: scoreColor(val), transition: 'width 0.6s ease' }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
