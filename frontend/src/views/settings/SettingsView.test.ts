import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/auth'
import SettingsView from './SettingsView.vue'

const stubs = {
  BasicPage: { template: '<main><slot /></main>' },
  AppearanceSettingsCard: { template: '<div data-testid="appearance-card" />' },
  NotificationSettingsCard: { template: '<div data-testid="notification-card" />' },
  SystemParamsCard: { template: '<div data-testid="system-card" />' },
  AccountSecurityCard: { template: '<div data-testid="account-card" />' },
}

function mountPage(role: 'admin' | 'trader') {
  const auth = useAuthStore()
  auth.user = {
    id: 'u1',
    username: 'alice',
    role,
    is_active: true,
    created_at: '',
  }
  return mount(SettingsView, { global: { stubs } })
}

describe('SettingsView', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('shows all four cards to administrators', () => {
    const wrapper = mountPage('admin')
    expect(wrapper.find('[data-testid="appearance-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="notification-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="system-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="account-card"]').exists()).toBe(true)
  })

  it('does not render system parameters for ordinary users', () => {
    const wrapper = mountPage('trader')
    expect(wrapper.find('[data-testid="system-card"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="appearance-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="notification-card"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="account-card"]').exists()).toBe(true)
  })
})
