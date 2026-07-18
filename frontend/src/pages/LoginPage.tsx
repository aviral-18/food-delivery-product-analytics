import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { UtensilsCrossed, ArrowRight } from 'lucide-react'
import { useAuth } from '@/state/AuthProvider'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/misc'

const DEMO = [
  { role: 'Product Manager', email: 'pm@eternal.dev', password: 'pm123456' },
  { role: 'Product Analyst', email: 'analyst@eternal.dev', password: 'analyst123' },
  { role: 'Admin', email: 'admin@eternal.dev', password: 'admin123' },
]

export function LoginPage() {
  const { user, login } = useAuth()
  const [email, setEmail] = useState('pm@eternal.dev')
  const [password, setPassword] = useState('pm123456')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      await login(email, password)
    } catch (err) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Login failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-screen bg-page lg:grid-cols-2">
      {/* Left brand panel */}
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-border bg-surface p-10 lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-60"
          style={{
            background:
              'radial-gradient(600px 400px at 20% 10%, var(--primary-soft), transparent), radial-gradient(500px 400px at 80% 90%, color-mix(in srgb, var(--chart-7) 18%, transparent), transparent)',
          }}
        />
        <div className="relative flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-fg">
            <UtensilsCrossed className="h-5 w-5" />
          </div>
          <div>
            <div className="font-semibold text-ink">Eternal</div>
            <div className="text-[11px] uppercase tracking-wider text-muted">Product Analytics</div>
          </div>
        </div>
        <div className="relative">
          <h2 className="max-w-md text-2xl font-semibold leading-snug text-ink">
            The internal analytics platform Product Managers use to make decisions.
          </h2>
          <p className="mt-3 max-w-md text-[14px] leading-relaxed text-ink-2">
            Retention & cohorts, RFM & CLV, delivery operations, coupon economics, forecasting, AI
            insights, and a decision simulator — every page answers a business question.
          </p>
        </div>
        <div className="relative text-[12px] text-muted">
          101,922 orders · 30,000 customers · 2,000 restaurants · 24 months
        </div>
      </div>

      {/* Right form */}
      <div className="flex items-center justify-center p-6">
        <div className="w-full max-w-sm">
          <h1 className="text-xl font-semibold text-ink">Sign in</h1>
          <p className="mt-1 text-[13px] text-ink-2">Use a demo account below to explore the platform.</p>

          <form onSubmit={submit} className="mt-6 flex flex-col gap-3">
            <label className="flex flex-col gap-1.5">
              <span className="text-[13px] font-medium text-ink-2">Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-10 rounded-md border border-border bg-surface px-3 text-[14px] text-ink outline-none focus:border-primary"
              />
            </label>
            <label className="flex flex-col gap-1.5">
              <span className="text-[13px] font-medium text-ink-2">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-10 rounded-md border border-border bg-surface px-3 text-[14px] text-ink outline-none focus:border-primary"
              />
            </label>
            {error && <p className="text-[13px] text-[var(--critical)]">{error}</p>}
            <Button type="submit" size="lg" disabled={busy} className="mt-1">
              {busy ? <Spinner className="h-4 w-4" /> : <>Sign in <ArrowRight className="h-4 w-4" /></>}
            </Button>
          </form>

          <div className="mt-6">
            <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-muted">Demo accounts</div>
            <div className="flex flex-col gap-1.5">
              {DEMO.map((d) => (
                <button
                  key={d.email}
                  onClick={() => {
                    setEmail(d.email)
                    setPassword(d.password)
                  }}
                  className="flex items-center justify-between rounded-md border border-border bg-surface px-3 py-2 text-left text-[13px] hover:bg-surface-2"
                >
                  <span className="font-medium text-ink">{d.role}</span>
                  <span className="text-muted">{d.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
