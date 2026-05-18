import { useQuery, useMutation } from '@tanstack/vue-query'
import { settingsApi } from '@/api/settings'
import { queryClient } from '@/plugins/vue-query'
import type { TradingModeConfig, PasswordChangeRequest } from '@/types/settings'

export function useProfile() {
  return useQuery({
    queryKey: ['settings', 'profile'],
    queryFn: async () => ((await settingsApi.getProfile()) as any).data,
  })
}

export function useBrokers() {
  return useQuery({
    queryKey: ['settings', 'brokers'],
    queryFn: async () => ((await settingsApi.getBrokers()) as any).data,
  })
}

export function useTradingMode() {
  return useQuery({
    queryKey: ['settings', 'trading-mode'],
    queryFn: async () => ((await settingsApi.getTradingMode()) as any).data,
  })
}

export function useNotifications() {
  return useQuery({
    queryKey: ['settings', 'notifications'],
    queryFn: async () => ((await settingsApi.getNotifications()) as any).data,
  })
}

export function useParams() {
  return useQuery({
    queryKey: ['settings', 'params'],
    queryFn: async () => ((await settingsApi.getParams()) as any).data,
  })
}

export function useUpdateBroker() {
  return useMutation({
    mutationFn: ({ brokerName, data }: { brokerName: string; data: Record<string, any> }) =>
      settingsApi.updateBroker(brokerName, data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useTestBroker() {
  return useMutation({
    mutationFn: (brokerName: string) => settingsApi.testBroker(brokerName) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useUpdateTradingMode() {
  return useMutation({
    mutationFn: (data: TradingModeConfig) => settingsApi.updateTradingMode(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useUpdateNotifications() {
  return useMutation({
    mutationFn: (data: Record<string, any>) => settingsApi.updateNotifications(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useTestEmail() {
  return useMutation({
    mutationFn: () => settingsApi.testEmail() as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useTestWebhook() {
  return useMutation({
    mutationFn: () => settingsApi.testWebhook() as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useUpdateParams() {
  return useMutation({
    mutationFn: (data: Record<string, any>) => settingsApi.updateParams(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useResetParams() {
  return useMutation({
    mutationFn: () => settingsApi.resetParams() as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (data: PasswordChangeRequest) => settingsApi.changePassword(data) as any,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}
