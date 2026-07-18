import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useAuth } from '@/state/AuthProvider'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatTiles } from '@/components/dashboard/StatTiles'
import { Badge, LoadingState } from '@/components/ui/misc'
import { formatNumber } from '@/lib/utils'
import type { User } from '@/types'

interface Overview {
  counts: Record<string, number>
  active_customers: number
  active_restaurants: number
}
interface AuditLog {
  id: number
  user_id: number | null
  action: string
  entity: string | null
  detail: string | null
  created_at: string | null
}

export function AdminPage() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const overview = useQuery({
    queryKey: ['admin-overview'],
    queryFn: async () => (await api.get<Overview>('/admin/overview')).data,
  })
  const users = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => (await api.get<User[]>('/admin/users')).data,
    enabled: isAdmin,
  })
  const audit = useQuery({
    queryKey: ['admin-audit'],
    queryFn: async () => (await api.get<{ logs: AuditLog[] }>('/admin/audit-logs', { params: { limit: 40 } })).data.logs,
    enabled: isAdmin,
  })

  if (overview.isLoading) return <LoadingState label="Loading admin console…" />
  const c = overview.data?.counts ?? {}

  return (
    <div className="space-y-5">
      <StatTiles
        stats={[
          { label: 'Orders', value: formatNumber(c.orders) },
          { label: 'Customers', value: formatNumber(c.customers) },
          { label: 'Restaurants', value: formatNumber(c.restaurants) },
          { label: 'Delivery Partners', value: formatNumber(c.delivery_partners) },
        ]}
      />
      <StatTiles
        stats={[
          { label: 'Cities', value: formatNumber(c.cities) },
          { label: 'Coupons', value: formatNumber(c.coupons) },
          { label: 'Platform Users', value: formatNumber(c.users) },
          { label: 'Audit Log Entries', value: formatNumber(c.audit_logs) },
        ]}
      />

      {isAdmin ? (
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle>Platform users</CardTitle></CardHeader>
            <CardContent>
              <div className="overflow-auto rounded-[var(--radius-md)] border border-border">
                <table className="w-full text-[13px]">
                  <thead className="bg-surface-2">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium text-ink-2">Name</th>
                      <th className="px-3 py-2 text-left font-medium text-ink-2">Role</th>
                      <th className="px-3 py-2 text-left font-medium text-ink-2">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.data?.map((u) => (
                      <tr key={u.id} className="border-t border-border">
                        <td className="px-3 py-2">
                          <div className="font-medium text-ink">{u.full_name}</div>
                          <div className="text-[11px] text-muted">{u.email}</div>
                        </td>
                        <td className="px-3 py-2 capitalize text-ink-2">{u.role.replace(/_/g, ' ')}</td>
                        <td className="px-3 py-2">
                          {u.is_active ? <Badge tone="good">active</Badge> : <Badge tone="critical">disabled</Badge>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Audit log</CardTitle></CardHeader>
            <CardContent>
              <div className="max-h-[360px] space-y-1.5 overflow-y-auto">
                {audit.data?.map((a) => (
                  <div key={a.id} className="flex items-center gap-2 rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[12px]">
                    <Badge tone="primary">{a.action}</Badge>
                    <span className="text-ink-2">{a.entity ?? '—'}</span>
                    <span className="ml-auto tabnum text-muted">
                      {a.created_at ? new Date(a.created_at).toLocaleString() : ''}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="py-10 text-center text-[13px] text-ink-2">
            User management and audit logs require the <span className="font-medium text-ink">Admin</span> role.
          </CardContent>
        </Card>
      )}
    </div>
  )
}
