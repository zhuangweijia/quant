import { useQuery, useMutation } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import { riskApi } from '@/api/risk'
import { queryClient } from '@/plugins/vue-query'
import type { RiskRuleCreateRequest, RiskRuleUpdateRequest } from '@/types/risk'

export function useRiskRules() {
  return useQuery({
    queryKey: ['risk', 'rules'],
    queryFn: async () => ((await riskApi.getRules()) as any).data,
  })
}

export function useRiskAlerts(params?: MaybeRefOrGetter<Record<string, any>>) {
  return useQuery({
    queryKey: ['risk', 'alerts', params],
    queryFn: async () => ((await riskApi.getAlerts(toValue(params))) as any).data,
  })
}

export function useUnreadAlertCount() {
  return useQuery({
    queryKey: ['risk', 'unread-count'],
    queryFn: async () => ((await riskApi.getUnreadCount()) as any).data,
  })
}

export function useCreateRule() {
  return useMutation({
    mutationFn: (data: RiskRuleCreateRequest) => riskApi.createRule(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk'] })
    },
  })
}

export function useUpdateRule() {
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: RiskRuleUpdateRequest }) =>
      riskApi.updateRule(id, data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk'] })
    },
  })
}

export function useToggleRule() {
  return useMutation({
    mutationFn: (id: string) => riskApi.toggleRule(id) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk'] })
    },
  })
}

export function useDeleteRule() {
  return useMutation({
    mutationFn: (id: string) => riskApi.deleteRule(id) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk'] })
    },
  })
}

export function useMarkAlertRead() {
  return useMutation({
    mutationFn: (id: string) => riskApi.markAlertRead(id) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk'] })
    },
  })
}

export function useMarkAllAlertsRead() {
  return useMutation({
    mutationFn: () => riskApi.markAllAlertsRead() as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['risk'] })
    },
  })
}
