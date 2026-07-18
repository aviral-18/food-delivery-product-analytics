import { Suspense } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Topbar } from './Topbar'
import { FilterBar } from './FilterBar'
import { LoadingState } from '@/components/ui/misc'
import { NAV } from '@/nav'

const SUBTITLES: Record<string, string> = {
  '/': 'The single pane of glass for product & business health',
  '/customers/cohorts': 'Are newer cohorts retaining as well as older ones?',
  '/customers/rfm': 'Which customers matter most, and who is slipping away?',
  '/customers/clv': 'Which segments and channels generate the most lifetime value?',
  '/customers/repeat': 'What drives customers to come back — and when?',
  '/customers/frequency': 'How often do customers actually order?',
  '/customers/funnel': 'Where do we lose people between signup and loyalty?',
  '/operations/delivery': 'Are we keeping the on-time promise?',
  '/operations/delay': 'What is actually causing delivery delays?',
  '/operations/cancellations': 'Why are orders being cancelled?',
  '/operations/refunds': 'What is driving refunds and how much do they cost?',
  '/operations/peak': 'When is demand concentrated across the week?',
  '/catalog/restaurants': 'Which restaurants drive the business and which hurt experience?',
  '/catalog/cuisines': 'Which cuisines are most profitable?',
  '/catalog/cities': 'Which cities deserve more investment?',
  '/marketing/coupons': 'Are coupons creating profit — or just orders?',
  '/marketing/efficiency': 'How efficient is our acquisition spend?',
  '/forecast': 'Where are the key metrics heading?',
  '/decision-lab': 'Simulate product & pricing decisions before you ship them',
  '/sql-explorer': 'The SQL behind every metric, runnable live',
  '/admin': 'Platform administration & governance',
}

function titleForPath(path: string): string {
  for (const group of NAV) {
    for (const item of group.items) {
      if (item.path === path) return item.label
    }
  }
  return 'Analytics'
}

export function AppShell() {
  const { pathname } = useLocation()
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar title={titleForPath(pathname)} subtitle={SUBTITLES[pathname]} />
        <FilterBar />
        <main className="flex-1 overflow-y-auto bg-page">
          <div className="mx-auto max-w-[1400px] p-5">
            <Suspense fallback={<LoadingState label="Loading page…" />}>
              <Outlet />
            </Suspense>
          </div>
        </main>
      </div>
    </div>
  )
}
