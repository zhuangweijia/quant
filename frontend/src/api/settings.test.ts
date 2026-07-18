import { beforeEach, describe, expect, it, vi } from 'vitest'

import client from './client'
import { settingsApi, type NotificationUpdate, type SystemParams } from './settings'

const params: SystemParams = {
  data_retention_days: 90,
  alert_retention_days: 90,
  model_train_window_days: 756,
  model_val_window_days: 126,
  forward_return_days: 5,
  forward_return_threshold: 0.02,
  model_ic_threshold: 0.02,
  stock_universe: 'csi300',
  analysis_time: '17:00',
}

describe('settingsApi', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('sends password fields required by the backend', async () => {
    vi.spyOn(client, 'put').mockResolvedValue({ data: null } as never)

    await settingsApi.changePassword({
      old_password: 'oldpass1',
      new_password: 'newpass2',
      confirm_password: 'newpass2',
    })

    expect(client.put).toHaveBeenCalledWith('/api/v1/settings/password', {
      old_password: 'oldpass1',
      new_password: 'newpass2',
      confirm_password: 'newpass2',
    })
  })

  it('exposes notification save and test endpoints', async () => {
    vi.spyOn(client, 'put').mockResolvedValue({ data: { saved: true } } as never)
    vi.spyOn(client, 'post').mockResolvedValue({ data: { sent: true } } as never)
    const payload: NotificationUpdate = {
      email_enabled: true,
      email_smtp_host: 'smtp.example.com',
      email_smtp_port: 465,
      email_sender: 'sender@example.com',
      email_password: '',
      email_use_ssl: true,
      email_recipient: 'alerts@example.com',
      webhook_enabled: false,
      webhook_url: '',
      webhook_secret: '',
      notify_levels: ['warning', 'error'],
    }

    await settingsApi.updateNotifications(payload)
    await settingsApi.testEmail()
    await settingsApi.testWebhook()

    expect(client.put).toHaveBeenCalledWith('/api/v1/settings/notifications', payload)
    expect(client.post).toHaveBeenCalledWith('/api/v1/settings/notifications/test-email')
    expect(client.post).toHaveBeenCalledWith('/api/v1/settings/notifications/test-webhook')
  })

  it('wraps system parameters in the backend request envelope', async () => {
    vi.spyOn(client, 'put').mockResolvedValue({ data: params } as never)

    await settingsApi.updateParams(params)

    expect(client.put).toHaveBeenCalledWith('/api/v1/settings/params', { params })
  })
})
