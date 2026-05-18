import { useQuery, useMutation } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import { tradeApi } from '@/api/trade'
import { queryClient } from '@/plugins/vue-query'
import type { OrderRequest } from '@/types/trade'

export function usePositions() {
  return useQuery({
    queryKey: ['trade', 'positions'],
    queryFn: async () => ((await tradeApi.getPositions()) as any).data,
  })
}

export function useOrders(params?: MaybeRefOrGetter<Record<string, any>>) {
  return useQuery({
    queryKey: ['trade', 'orders', params],
    queryFn: async () => ((await tradeApi.getOrders(toValue(params))) as any).data,
  })
}

export function useAccount() {
  return useQuery({
    queryKey: ['trade', 'account'],
    queryFn: async () => ((await tradeApi.getAccount()) as any).data,
  })
}

export function useSubmitOrder() {
  return useMutation({
    mutationFn: (data: OrderRequest) => tradeApi.submitOrder(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trade'] })
    },
  })
}

export function useCancelOrder() {
  return useMutation({
    mutationFn: (orderId: string) => tradeApi.cancelOrder(orderId) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trade'] })
    },
  })
}

export function useClosePosition() {
  return useMutation({
    mutationFn: (positionId: string) => tradeApi.closePosition(positionId) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trade'] })
    },
  })
}
