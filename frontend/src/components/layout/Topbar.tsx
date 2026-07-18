import { Moon, Sun, LogOut } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '@/state/AuthProvider'
import { useTheme } from '@/state/ThemeProvider'
import { Button } from '@/components/ui/button'
import { ExportButton } from '@/components/ExportButton'

const ROLE_LABEL: Record<string, string> = {
  admin: 'Admin',
  product_manager: 'Product Manager',
  product_analyst: 'Product Analyst',
}

// Routes that map to a backend export report.
const ROUTE_EXPORT: Record<string, string> = {
  '/catalog/cities': 'city-performance',
  '/catalog/restaurants': 'restaurant-performance',
  '/catalog/cuisines': 'cuisine-performance',
  '/marketing/coupons': 'coupon-effectiveness',
  '/customers/rfm': 'rfm-segments',
  '/customers/clv': 'clv-deciles',
}

export function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  const { user, logout } = useAuth()
  const { theme, toggle } = useTheme()
  const { pathname } = useLocation()
  const exportReport = ROUTE_EXPORT[pathname]

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between gap-4 border-b border-border bg-[var(--glass)] px-5 backdrop-blur-md">
      <div className="min-w-0">
        <h1 className="truncate text-[15px] font-semibold text-ink">{title}</h1>
        {subtitle && <p className="truncate text-[12px] text-ink-2">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-2">
        {exportReport && <ExportButton report={exportReport} />}
        <Button variant="ghost" size="icon" onClick={toggle} aria-label="Toggle theme">
          {theme === 'dark' ? <Sun className="h-[18px] w-[18px]" /> : <Moon className="h-[18px] w-[18px]" />}
        </Button>
        <div className="mx-1 hidden text-right sm:block">
          <div className="text-[13px] font-medium text-ink">{user?.full_name}</div>
          <div className="text-[11px] text-muted">{ROLE_LABEL[user?.role ?? ''] ?? user?.role}</div>
        </div>
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-soft text-[12px] font-semibold text-primary">
          {user?.full_name?.split(' ').map((s) => s[0]).slice(0, 2).join('')}
        </div>
        <Button variant="ghost" size="icon" onClick={logout} aria-label="Log out">
          <LogOut className="h-[17px] w-[17px]" />
        </Button>
      </div>
    </header>
  )
}
