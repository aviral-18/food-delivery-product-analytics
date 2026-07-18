export interface User {
  id: number
  email: string
  full_name: string
  role: 'admin' | 'product_manager' | 'product_analyst'
  is_active: boolean
  last_login?: string | null
}

export interface GlobalFilters {
  start_date?: string
  end_date?: string
  city_ids?: number[]
  cuisine_ids?: number[]
  restaurant_ids?: number[]
  statuses?: string[]
  partner_ids?: number[]
  payment_methods?: string[]
  coupon_ids?: number[]
  channels?: string[]
  day_parts?: string[]
  is_weekend?: boolean
  is_festival?: boolean
}

export interface KpiCard {
  key: string
  value: number
  format: 'currency' | 'percent' | 'number' | 'minutes'
  delta_pct: number | null
  trend: 'up' | 'down' | null
  is_positive: boolean | null
}

export interface Insight {
  type: string
  severity: 'positive' | 'low' | 'medium' | 'high'
  title: string
  detail: string
  metric?: string | null
}

export interface ReferenceData {
  cities: { id: number; name: string; tier: number; region: string; state: string }[]
  cuisines: { id: number; name: string; category: string }[]
  coupons: { id: number; code: string; campaign_name: string }[]
  delivery_partners: { id: number; name: string; city_id: number }[]
  filter_options: {
    statuses: string[]
    payment_methods: string[]
    day_parts: string[]
    channels: string[]
    weather: string[]
  }
}
