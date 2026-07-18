import { lazy, type ReactNode } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '@/state/AuthProvider'
import { FiltersProvider } from '@/state/FiltersProvider'
import { AppShell } from '@/components/layout/AppShell'
import { LoadingState } from '@/components/ui/misc'
import { LoginPage } from '@/pages/LoginPage'

// Lazy-load analysis pages so the initial bundle stays lean (charts load on demand).
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const CohortsPage = lazy(() => import('@/pages/customers/CohortsPage').then((m) => ({ default: m.CohortsPage })))
const RfmPage = lazy(() => import('@/pages/customers/RfmPage').then((m) => ({ default: m.RfmPage })))
const ClvPage = lazy(() => import('@/pages/customers/ClvPage').then((m) => ({ default: m.ClvPage })))
const RepeatPage = lazy(() => import('@/pages/customers/RepeatPage').then((m) => ({ default: m.RepeatPage })))
const FrequencyPage = lazy(() => import('@/pages/customers/FrequencyPage').then((m) => ({ default: m.FrequencyPage })))
const FunnelPage = lazy(() => import('@/pages/customers/FunnelPage').then((m) => ({ default: m.FunnelPage })))
const DeliveryPage = lazy(() => import('@/pages/operations/DeliveryPage').then((m) => ({ default: m.DeliveryPage })))
const DelayPage = lazy(() => import('@/pages/operations/DelayPage').then((m) => ({ default: m.DelayPage })))
const CancellationsPage = lazy(() => import('@/pages/operations/CancellationsPage').then((m) => ({ default: m.CancellationsPage })))
const RefundsPage = lazy(() => import('@/pages/operations/RefundsPage').then((m) => ({ default: m.RefundsPage })))
const PeakPage = lazy(() => import('@/pages/operations/PeakPage').then((m) => ({ default: m.PeakPage })))
const RestaurantsPage = lazy(() => import('@/pages/catalog/RestaurantsPage').then((m) => ({ default: m.RestaurantsPage })))
const CuisinesPage = lazy(() => import('@/pages/catalog/CuisinesPage').then((m) => ({ default: m.CuisinesPage })))
const CitiesPage = lazy(() => import('@/pages/catalog/CitiesPage').then((m) => ({ default: m.CitiesPage })))
const CouponsPage = lazy(() => import('@/pages/marketing/CouponsPage').then((m) => ({ default: m.CouponsPage })))
const EfficiencyPage = lazy(() => import('@/pages/marketing/EfficiencyPage').then((m) => ({ default: m.EfficiencyPage })))
const ForecastPage = lazy(() => import('@/pages/ForecastPage').then((m) => ({ default: m.ForecastPage })))
const DecisionLabPage = lazy(() => import('@/pages/DecisionLabPage').then((m) => ({ default: m.DecisionLabPage })))
const SqlExplorerPage = lazy(() => import('@/pages/SqlExplorerPage').then((m) => ({ default: m.SqlExplorerPage })))
const AdminPage = lazy(() => import('@/pages/AdminPage').then((m) => ({ default: m.AdminPage })))

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth()
  if (loading)
    return (
      <div className="flex h-screen items-center justify-center bg-page">
        <LoadingState label="Loading workspace…" />
      </div>
    )
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <Protected>
              <FiltersProvider>
                <AppShell />
              </FiltersProvider>
            </Protected>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="/customers/cohorts" element={<CohortsPage />} />
          <Route path="/customers/rfm" element={<RfmPage />} />
          <Route path="/customers/clv" element={<ClvPage />} />
          <Route path="/customers/repeat" element={<RepeatPage />} />
          <Route path="/customers/frequency" element={<FrequencyPage />} />
          <Route path="/customers/funnel" element={<FunnelPage />} />
          <Route path="/operations/delivery" element={<DeliveryPage />} />
          <Route path="/operations/delay" element={<DelayPage />} />
          <Route path="/operations/cancellations" element={<CancellationsPage />} />
          <Route path="/operations/refunds" element={<RefundsPage />} />
          <Route path="/operations/peak" element={<PeakPage />} />
          <Route path="/catalog/restaurants" element={<RestaurantsPage />} />
          <Route path="/catalog/cuisines" element={<CuisinesPage />} />
          <Route path="/catalog/cities" element={<CitiesPage />} />
          <Route path="/marketing/coupons" element={<CouponsPage />} />
          <Route path="/marketing/efficiency" element={<EfficiencyPage />} />
          <Route path="/forecast" element={<ForecastPage />} />
          <Route path="/decision-lab" element={<DecisionLabPage />} />
          <Route path="/sql-explorer" element={<SqlExplorerPage />} />
          <Route path="/admin" element={<AdminPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
