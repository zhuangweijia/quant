import { useQuery, useMutation } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import { backtestApi } from '@/api/backtest'
import { queryClient } from '@/plugins/vue-query'
import type { BacktestRunRequest } from '@/types/backtest'

export function useBacktestResults(params?: MaybeRefOrGetter<Record<string, any>>) {
  return useQuery({
    queryKey: ['backtest', 'results', params],
    queryFn: async () => ((await backtestApi.listResults(toValue(params))) as any).data,
  })
}

export function useBacktestResult(id: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: ['backtest', 'result', id],
    queryFn: async () => ((await backtestApi.getResult(toValue(id))) as any).data,
    enabled: () => !!toValue(id),
  })
}

export function useRunBacktest() {
  return useMutation({
    mutationFn: (data: BacktestRunRequest) => backtestApi.run(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtest'] })
    },
  })
}

export function useDeleteBacktestResult() {
  return useMutation({
    mutationFn: (id: string) => backtestApi.deleteResult(id) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtest'] })
    },
  })
}
