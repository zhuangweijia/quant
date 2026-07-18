import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { settingsApi, type NotificationSettings } from '@/api/settings'
import NotificationSettingsCard from './NotificationSettingsCard.vue'

vi.mock('vue-sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const saved: NotificationSettings = {
  email_enabled: true,
  email_smtp_host: 'smtp.example.com',
  email_smtp_port: 465,
  email_sender: 'sender@example.com',
  has_email_password: true,
  email_use_ssl: true,
  email_recipient: 'alerts@example.com',
  webhook_enabled: false,
  webhook_url: '',
  has_webhook_secret: true,
  notify_levels: ['warning', 'error'],
}

describe('NotificationSettingsCard', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    vi.spyOn(settingsApi, 'getNotifications').mockResolvedValue({ data: saved } as never)
  })

  it('shows configured-secret status without filling plaintext inputs', async () => {
    const wrapper = mount(NotificationSettingsCard)
    await flushPromises()
    expect(wrapper.get('[data-testid="email-password-configured"]').text()).toContain('已配置')
    expect((wrapper.get('#email-password').element as HTMLInputElement).value).toBe('')
  })

  it('preserves secrets by submitting blank replacement fields', async () => {
    const update = vi
      .spyOn(settingsApi, 'updateNotifications')
      .mockResolvedValue({ data: { saved: true } } as never)
    const wrapper = mount(NotificationSettingsCard)
    await flushPromises()
    await wrapper.get('#email-recipient').setValue('new@example.com')
    await wrapper.get('[data-testid="notification-save"]').trigger('click')
    await flushPromises()
    expect(update).toHaveBeenCalledWith(
      expect.objectContaining({ email_password: '', webhook_secret: '' }),
    )
  })

  it('disables test email while the form is dirty', async () => {
    const wrapper = mount(NotificationSettingsCard)
    await flushPromises()
    await wrapper.get('#email-recipient').setValue('dirty@example.com')
    expect(
      wrapper.get('[data-testid="notification-test-email"]').attributes('disabled'),
    ).toBeDefined()
  })

  it('sends a test email only from saved valid configuration', async () => {
    const testEmail = vi
      .spyOn(settingsApi, 'testEmail')
      .mockResolvedValue({ data: { sent: true } } as never)
    const wrapper = mount(NotificationSettingsCard)
    await flushPromises()
    expect(
      wrapper.get('[data-testid="notification-test-email"]').attributes('disabled'),
    ).toBeUndefined()
    await wrapper.get('[data-testid="notification-test-email"]').trigger('click')
    await flushPromises()
    expect(testEmail).toHaveBeenCalledOnce()
  })
})
