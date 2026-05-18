import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import { dashboardApi } from '@/api/dashboard'

export function useDashboardOverview() {
  return useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: async () => ((await dashboardApi.getOverview()) as any).data,
  })
}

export function useDashboardEquityCurve(range?: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: ['dashboard', 'equity-curve', range],
    queryFn: async () => ((await dashboardApi.getEquityCurve({ range: toValue(range) })) as any).data,
  })
}

export function useDashboardStrategyRanking() {
  return useQuery({
    queryKey: ['dashboard', 'strategy-ranking'],
    queryFn: async () => ((await dashboardApi.getStrategyRanking()) as any).data,
  })
}
