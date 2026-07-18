import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Play, Terminal, Clock, Database } from 'lucide-react'
import { api } from '@/lib/api'
import { useFilters } from '@/state/FiltersProvider'
import { useAuth } from '@/state/AuthProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/misc'
import { cn } from '@/lib/utils'

interface CatalogQuery {
  key: string
  category: string
  title: string
  business_question: string
  explanation: string
  sql: string
}
interface RunResult {
  sql: string
  execution_ms: number
  columns: string[]
  rows: Record<string, unknown>[]
  row_count: number
}

function ResultTable({ result }: { result: RunResult }) {
  if (!result.columns.length) return <p className="py-6 text-center text-[13px] text-muted">No columns returned.</p>
  return (
    <div className="overflow-auto rounded-[var(--radius-md)] border border-border" style={{ maxHeight: 360 }}>
      <table className="w-full border-collapse text-[12px]">
        <thead className="sticky top-0 bg-surface-2">
          <tr>
            {result.columns.map((c) => (
              <th key={c} className="whitespace-nowrap border-b border-border px-3 py-2 text-left font-medium text-ink-2">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {result.rows.map((row, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              {result.columns.map((c) => (
                <td key={c} className="whitespace-nowrap px-3 py-1.5 tabnum text-ink">
                  {typeof row[c] === 'number' ? (row[c] as number).toLocaleString('en-IN') : String(row[c] ?? '—')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SqlBlock({ sql }: { sql: string }) {
  return (
    <pre className="overflow-x-auto rounded-[var(--radius-md)] border border-border bg-[#0d0d10] p-3 text-[12px] leading-relaxed text-[#c9d1d9]">
      <code>{sql.trim()}</code>
    </pre>
  )
}

export function SqlExplorerPage() {
  const { filters } = useFilters()
  const { user } = useAuth()
  const canRunAdhoc = user?.role === 'admin' || user?.role === 'product_analyst'

  const { data: list } = useQuery({
    queryKey: ['sql-queries'],
    queryFn: async () => (await api.get<{ queries: CatalogQuery[] }>('/sql/queries')).data.queries,
    staleTime: Infinity,
  })

  const [selected, setSelected] = useState<string | null>(null)
  const [result, setResult] = useState<RunResult | null>(null)
  const [running, setRunning] = useState(false)

  const grouped = useMemo(() => {
    const g: Record<string, CatalogQuery[]> = {}
    for (const q of list ?? []) (g[q.category] ??= []).push(q)
    return g
  }, [list])

  const current = list?.find((q) => q.key === selected)

  useEffect(() => {
    if (!selected || !list) return
    setRunning(true)
    api
      .get<RunResult>(`/sql/queries/${selected}`, { params: { ...filters, limit: 100 } })
      .then((r) => setResult(r.data))
      .finally(() => setRunning(false))
  }, [selected, filters, list])

  // Ad-hoc console
  const [adhoc, setAdhoc] = useState('SELECT city_id, COUNT(*) AS orders\nFROM orders\nGROUP BY city_id\nORDER BY orders DESC')
  const [adhocResult, setAdhocResult] = useState<RunResult | null>(null)
  const [adhocErr, setAdhocErr] = useState('')
  const [adhocRunning, setAdhocRunning] = useState(false)
  async function runAdhoc() {
    setAdhocErr('')
    setAdhocRunning(true)
    try {
      const r = await api.post<RunResult>('/sql/execute', { sql: adhoc, limit: 200 })
      setAdhocResult(r.data)
    } catch (e) {
      setAdhocErr((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Query failed')
    } finally {
      setAdhocRunning(false)
    }
  }

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
      {/* Catalogue */}
      <Card className="lg:col-span-1">
        <CardHeader><CardTitle className="flex items-center gap-2"><Database className="h-4 w-4 text-primary" /> Metric queries</CardTitle></CardHeader>
        <CardContent className="max-h-[640px] space-y-4 overflow-y-auto">
          {Object.entries(grouped).map(([cat, qs]) => (
            <div key={cat}>
              <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted">{cat}</div>
              <div className="flex flex-col gap-0.5">
                {qs.map((q) => (
                  <button
                    key={q.key}
                    onClick={() => setSelected(q.key)}
                    className={cn(
                      'rounded-md px-2.5 py-1.5 text-left text-[13px] transition-colors',
                      selected === q.key ? 'bg-primary-soft text-primary' : 'text-ink-2 hover:bg-surface-2 hover:text-ink',
                    )}
                  >
                    {q.title}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Detail + results */}
      <div className="space-y-5 lg:col-span-2">
        {current ? (
          <Card>
            <CardHeader>
              <CardTitle>{current.title}</CardTitle>
              <span className="text-[13px] text-ink-2">{current.business_question}</span>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-[13px] text-ink-2">{current.explanation}</p>
              <SqlBlock sql={current.sql} />
              <div className="flex items-center gap-3">
                {running ? <Spinner className="h-4 w-4" /> : result && (
                  <span className="flex items-center gap-1.5 text-[12px] text-muted">
                    <Clock className="h-3.5 w-3.5" /> {result.execution_ms} ms · {result.row_count} rows
                  </span>
                )}
              </div>
              {result && <ResultTable result={result} />}
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="py-16 text-center text-[13px] text-muted">
              Select a metric query to view its SQL and run it live.
            </CardContent>
          </Card>
        )}

        {canRunAdhoc && (
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2"><Terminal className="h-4 w-4 text-primary" /> Ad-hoc query console</CardTitle><span className="text-[12px] text-ink-2">Read-only. SELECT / WITH only.</span></CardHeader>
            <CardContent className="space-y-3">
              <textarea
                value={adhoc}
                onChange={(e) => setAdhoc(e.target.value)}
                spellCheck={false}
                className="h-32 w-full rounded-[var(--radius-md)] border border-border bg-[#0d0d10] p-3 font-mono text-[12px] text-[#c9d1d9] outline-none focus:border-primary"
              />
              <div className="flex items-center gap-3">
                <Button size="sm" onClick={runAdhoc} disabled={adhocRunning}>
                  {adhocRunning ? <Spinner className="h-4 w-4" /> : <Play className="h-3.5 w-3.5" />} Run query
                </Button>
                {adhocResult && !adhocErr && (
                  <span className="text-[12px] text-muted">{adhocResult.execution_ms} ms · {adhocResult.row_count} rows</span>
                )}
                {adhocErr && <span className="text-[12px] text-[var(--critical)]">{adhocErr}</span>}
              </div>
              {adhocResult && !adhocErr && <ResultTable result={adhocResult} />}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
