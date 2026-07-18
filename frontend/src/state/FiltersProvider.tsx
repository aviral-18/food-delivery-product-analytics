import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { GlobalFilters, ReferenceData } from '@/types'

/** Lookup helpers to turn city/cuisine IDs into human labels. */
export function useLabels() {
  const { reference } = useFilters()
  const cityMap = useMemo(
    () => new Map((reference?.cities ?? []).map((c) => [c.id, c.name])),
    [reference],
  )
  const cuisineMap = useMemo(
    () => new Map((reference?.cuisines ?? []).map((c) => [c.id, c.name])),
    [reference],
  )
  return {
    cityName: (id: number | null | undefined) => (id != null ? cityMap.get(id) ?? `City ${id}` : '—'),
    cuisineName: (id: number | null | undefined) => (id != null ? cuisineMap.get(id) ?? `Cuisine ${id}` : '—'),
  }
}

interface FiltersCtx {
  filters: GlobalFilters
  setFilters: (f: GlobalFilters) => void
  patch: (p: Partial<GlobalFilters>) => void
  reset: () => void
  activeCount: number
  reference?: ReferenceData
}

const Ctx = createContext<FiltersCtx>({
  filters: {},
  setFilters: () => {},
  patch: () => {},
  reset: () => {},
  activeCount: 0,
})

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<GlobalFilters>({})

  const { data: reference } = useQuery({
    queryKey: ['reference'],
    queryFn: async () => (await api.get<ReferenceData>('/meta/reference')).data,
    staleTime: Infinity,
  })

  const value = useMemo<FiltersCtx>(() => {
    const activeCount = Object.values(filters).filter(
      (v) => v !== undefined && v !== null && !(Array.isArray(v) && v.length === 0),
    ).length
    return {
      filters,
      setFilters,
      patch: (p) => setFilters((f) => ({ ...f, ...p })),
      reset: () => setFilters({}),
      activeCount,
      reference,
    }
  }, [filters, reference])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useFilters = () => useContext(Ctx)

/** Hook to run a filtered analytics GET query keyed by endpoint + filters. */
export function useAnalytics<T>(key: string, endpoint: string, extraParams: Record<string, unknown> = {}) {
  const { filters } = useFilters()
  return useQuery<T>({
    queryKey: [key, filters, extraParams],
    queryFn: async () => {
      const res = await api.get<T>(endpoint, { params: { ...filters, ...extraParams } })
      return res.data
    },
  })
}
