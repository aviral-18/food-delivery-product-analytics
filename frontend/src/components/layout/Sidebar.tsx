import { NavLink } from 'react-router-dom'
import { UtensilsCrossed } from 'lucide-react'
import { NAV } from '@/nav'
import { useAuth } from '@/state/AuthProvider'
import { cn } from '@/lib/utils'

export function Sidebar() {
  const { user } = useAuth()
  const role = user?.role ?? ''

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-surface md:flex">
      <div className="flex h-14 items-center gap-2.5 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-fg">
          <UtensilsCrossed className="h-[18px] w-[18px]" />
        </div>
        <div className="leading-tight">
          <div className="text-[15px] font-semibold text-ink">Eternal</div>
          <div className="text-[10px] font-medium uppercase tracking-wider text-muted">Product Analytics</div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        {NAV.map((group) => {
          const items = group.items.filter((i) => !i.roles || i.roles.includes(role))
          if (items.length === 0) return null
          return (
            <div key={group.group} className="mb-5">
              <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-wider text-muted">
                {group.group}
              </div>
              <div className="flex flex-col gap-0.5">
                {items.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    end={item.path === '/'}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium transition-colors',
                        isActive
                          ? 'bg-primary-soft text-primary'
                          : 'text-ink-2 hover:bg-surface-2 hover:text-ink',
                      )
                    }
                  >
                    <item.icon className="h-[17px] w-[17px] shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </NavLink>
                ))}
              </div>
            </div>
          )
        })}
      </nav>
    </aside>
  )
}
