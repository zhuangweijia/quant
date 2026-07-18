import client from './client'
import type { ResponseBase } from '@/types/common'

export type NotificationLevel = 'info' | 'warning' | 'error'

export interface NotificationSettings {
  email_enabled: boolean
  email_smtp_host: string
  email_smtp_port: number
  email_sender: string
  has_email_password: boolean
  email_use_ssl: boolean
  email_recipient: string
  webhook_enabled: boolean
  webhook_url: string
  has_webhook_secret: boolean
  notify_levels: NotificationLevel[]
}

export type NotificationUpdate = Omit<
  NotificationSettings,
  'has_email_password' | 'has_webhook_secret'
> & {
  email_password: string
  webhook_secret: string
}

export interface SystemParams {
  data_retention_days: number
  alert_retention_days: number
  model_train_window_days: number
  model_val_window_days: number
  forward_return_days: number
  forward_return_threshold: number
  model_ic_threshold: number
  stock_universe: 'csi300'
  analysis_time: string
}

export interface ProfileSettings {
  username: string
  role: string
  is_active: boolean
  created_at: string | null
}

export interface PasswordChange {
  old_password: string
  new_password: string
  confirm_password: string
}

type ApiResult<T> = Promise<ResponseBase<T>>

export const settingsApi = {
  getNotifications: () =>
    client.get<ResponseBase<NotificationSettings>>(
      '/api/v1/settings/notifications',
    ) as unknown as ApiResult<NotificationSettings>,
  updateNotifications: (data: NotificationUpdate) =>
    client.put<ResponseBase<{ saved: boolean }>>(
      '/api/v1/settings/notifications',
      data,
    ) as unknown as ApiResult<{ saved: boolean }>,
  testEmail: () =>
    client.post<ResponseBase<{ sent: boolean }>>(
      '/api/v1/settings/notifications/test-email',
    ) as unknown as ApiResult<{ sent: boolean }>,
  testWebhook: () =>
    client.post<ResponseBase<{ sent: boolean }>>(
      '/api/v1/settings/notifications/test-webhook',
    ) as unknown as ApiResult<{ sent: boolean }>,
  getParams: () =>
    client.get<ResponseBase<SystemParams>>(
      '/api/v1/settings/params',
    ) as unknown as ApiResult<SystemParams>,
  updateParams: (params: SystemParams) =>
    client.put<ResponseBase<SystemParams>>('/api/v1/settings/params', {
      params,
    }) as unknown as ApiResult<SystemParams>,
  resetParams: () =>
    client.post<ResponseBase<SystemParams>>(
      '/api/v1/settings/params/reset',
    ) as unknown as ApiResult<SystemParams>,
  getProfile: () =>
    client.get<ResponseBase<ProfileSettings>>(
      '/api/v1/settings/profile',
    ) as unknown as ApiResult<ProfileSettings>,
  changePassword: (data: PasswordChange) =>
    client.put<ResponseBase<null>>(
      '/api/v1/settings/password',
      data,
    ) as unknown as ApiResult<null>,
}
