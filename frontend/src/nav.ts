import {
  LayoutDashboard, Users, Repeat, Grid3x3, TrendingUp, Filter, Truck,
  Timer, XCircle, RotateCcw, Clock, Store, UtensilsCrossed, MapPin,
  Ticket, Megaphone, LineChart, FlaskConical, Terminal, Shield, type LucideIcon,
} from 'lucide-react'

export interface NavItem {
  label: string
  path: string
  icon: LucideIcon
  roles?: string[] // if set, only these roles see it
}

export interface NavGroup {
  group: string
  items: NavItem[]
}

export const NAV: NavGroup[] = [
  {
    group: 'Overview',
    items: [{ label: 'Executive Dashboard', path: '/', icon: LayoutDashboard }],
  },
  {
    group: 'Customers',
    items: [
      { label: 'Cohorts & Retention', path: '/customers/cohorts', icon: Grid3x3 },
      { label: 'RFM Segments', path: '/customers/rfm', icon: Users },
      { label: 'Lifetime Value', path: '/customers/clv', icon: TrendingUp },
      { label: 'Repeat Purchase', path: '/customers/repeat', icon: Repeat },
      { label: 'Order Frequency', path: '/customers/frequency', icon: LineChart },
      { label: 'Journey Funnel', path: '/customers/funnel', icon: Filter },
    ],
  },
  {
    group: 'Operations',
    items: [
      { label: 'Delivery Performance', path: '/operations/delivery', icon: Truck },
      { label: 'Delay Root Cause', path: '/operations/delay', icon: Timer },
      { label: 'Cancellations', path: '/operations/cancellations', icon: XCircle },
      { label: 'Refunds', path: '/operations/refunds', icon: RotateCcw },
      { label: 'Peak Hours', path: '/operations/peak', icon: Clock },
    ],
  },
  {
    group: 'Catalog & Geography',
    items: [
      { label: 'Restaurants', path: '/catalog/restaurants', icon: Store },
      { label: 'Cuisines', path: '/catalog/cuisines', icon: UtensilsCrossed },
      { label: 'Cities', path: '/catalog/cities', icon: MapPin },
    ],
  },
  {
    group: 'Marketing',
    items: [
      { label: 'Coupon Effectiveness', path: '/marketing/coupons', icon: Ticket },
      { label: 'Channel Efficiency', path: '/marketing/efficiency', icon: Megaphone },
    ],
  },
  {
    group: 'Planning',
    items: [
      { label: 'Forecasting', path: '/forecast', icon: LineChart },
      { label: 'Decision Lab', path: '/decision-lab', icon: FlaskConical },
      { label: 'SQL Explorer', path: '/sql-explorer', icon: Terminal, roles: ['admin', 'product_analyst'] },
    ],
  },
  {
    group: 'System',
    items: [{ label: 'Admin', path: '/admin', icon: Shield }],
  },
]
