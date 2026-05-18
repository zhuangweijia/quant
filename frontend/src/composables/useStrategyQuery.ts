import { useQuery, useMutation } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import { strategyApi, strategyLogApi } from '@/api/strategy'
import { queryClient } from '@/plugins/vue-query'
import type { StrategyCreateRequest, StrategyUpdateRequest } from '@/types/strategy'

export function useStrategyList(params?: MaybeRefOrGetter<Record<string, any>>) {
  return useQuery({
    queryKey: ['strategy', 'list', params],
    queryFn: async () => ((await strategyApi.list(toValue(params))) as any).data,
  })
}

export function useStrategyDetail(id: MaybeRefOrGetter<string>) {
  return useQuery({
    queryKey: ['strategy', 'detail', id],
    queryFn: async () => ((await strategyApi.get(toValue(id))) as any).data,
    enabled: () => !!toValue(id),
  })
}

export function useStrategyLogs(
  strategyId: MaybeRefOrGetter<string>,
  params?: MaybeRefOrGetter<Record<string, any>>,
) {
  return useQuery({
    queryKey: ['strategy', 'logs', strategyId, params],
    queryFn: async () => ((await strategyLogApi.list(toValue(strategyId), toValue(params))) as any).data,
    enabled: () => !!toValue(strategyId),
  })
}

export function useCreateStrategy() {
  return useMutation({
    mutationFn: (data: StrategyCreateRequest) => strategyApi.create(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy'] })
    },
  })
}

export function useUpdateStrategy() {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: StrategyUpdateRequest }) =>
      strategyApi.update(id, data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy'] })
    },
  })
}

export function useDeleteStrategy() {
  return useMutation({
    mutationFn: (id: string) => strategyApi.remove(id) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy'] })
    },
  })
}

export function useStartStrategy() {
  return useMutation({
    mutationFn: (id: string) => strategyApi.start(id) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy'] })
    },
  })
}

export function useStopStrategy() {
  return useMutation({
    mutationFn: (id: string) => strategyApi.stop(id) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy'] })
    },
  })
}
